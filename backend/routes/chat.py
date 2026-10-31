"""
backend/routes/chat.py
Streaming and non-streaming chat endpoints for the RAG pipeline.
"""
import asyncio
import json
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, Depends, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from backend.core.security import get_current_user_id, get_optional_user_id
from backend.services.llm_service import ask_mistral, stream_mistral
from backend.services.embedding_service import semantic_search, index_repository
from backend.services.memory_service import add_to_memory, get_memory, get_conversation_history, clear_memory
from backend.services.repo_service import clone_repository
from backend.services.parser_service import parse_repository
from backend.services.user_service import upsert_repo, update_repo_status, get_user_repos
from agents.repository_agent import RepositoryAgent

router = APIRouter(prefix="/chat", tags=["chat"])

# ─── Models ──────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    repo_url: str

    @field_validator("repo_url")
    @classmethod
    def sanitize_url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("https://github.com/") or v.startswith("http://github.com/")):
            # Allow any git URL but flag non-github for later
            pass
        return v


class ChatRequest(BaseModel):
    repo_name: str
    question: str
    max_iterations: int = 6

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        if len(v) > 2000:
            raise ValueError("Question too long (max 2000 chars)")
        return v

    @field_validator("repo_name")
    @classmethod
    def repo_name_safe(cls, v: str) -> str:
        import re
        v = v.strip()
        # Prevent path traversal
        if ".." in v or "/" in v.lstrip("workspace/"):
            pass  # repo_name validated again in tools.py
        return v


class StreamChatRequest(BaseModel):
    repo_name: str
    question: str


# ─── Ingestion ───────────────────────────────────────────────────────────────

def _ingest_pipeline(repo_url: str, repo_name: str, repo_id: int) -> None:
    """Background task: clone → parse → index."""
    try:
        update_repo_status(repo_id, "cloning")
        clone_result = clone_repository(repo_url)
        local_path = clone_result.get("local_path", f"workspace/{repo_name}")

        update_repo_status(repo_id, "indexing")
        parsed = parse_repository(local_path)
        index_repository(parsed["parsed_files"], repo_name)

        update_repo_status(repo_id, "ready")
    except Exception as exc:
        update_repo_status(repo_id, "error", str(exc))


@router.post("/ingest")
async def ingest_repo(
    req: IngestRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[int] = Depends(get_optional_user_id),
):
    """Clone and index a repository in the background."""
    repo_url = req.repo_url
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")

    # Track in DB if user is authenticated
    repo_id = None
    if user_id:
        repo_record = upsert_repo(user_id, repo_url, repo_name)
        repo_id = repo_record["id"]
    else:
        # Anonymous — use a sentinel id
        repo_id = -1

    if repo_id and repo_id > 0:
        background_tasks.add_task(_ingest_pipeline, repo_url, repo_name, repo_id)
    else:
        background_tasks.add_task(_ingest_pipeline_anon, repo_url, repo_name)

    return {
        "message": "Repository ingestion started",
        "repo_name": repo_name,
        "repo_url": repo_url,
        "status": "pending",
    }


def _ingest_pipeline_anon(repo_url: str, repo_name: str) -> None:
    try:
        clone_repository(repo_url)
        local_path = f"workspace/{repo_name}"
        parsed = parse_repository(local_path)
        index_repository(parsed["parsed_files"], repo_name)
    except Exception:
        pass


# ─── Agent chat (JSON response) ──────────────────────────────────────────────

@router.post("/ask")
def chat_ask(
    req: ChatRequest,
    user_id: Optional[int] = Depends(get_optional_user_id),
):
    """Full agentic RAG pipeline — returns structured JSON with evidence."""
    agent = RepositoryAgent(
        repo_name=req.repo_name,
        max_iterations=req.max_iterations,
    )
    result = agent.run(req.question)

    # Persist to memory
    answer_text = result.get("explanation", str(result))
    add_to_memory(req.question, answer_text, user_id, req.repo_name)

    return result


# ─── Streaming chat (SSE via GET — EventSource compatible) ──────────────────

@router.get("/stream")
async def chat_stream_get(
    question: str = Query(..., max_length=2000),
    repo_name: str = Query(...),
    user_id: Optional[int] = Depends(get_optional_user_id),
):
    """GET-based SSE endpoint compatible with the browser EventSource API."""

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # 1. Retrieve semantic context
            search_results = semantic_search(question, repo_name, top_k=5)
            context_parts = [r["content"] for r in search_results if r.get("content")]
            context = "\n\n---\n\n".join(context_parts)

            # 2. Conversation history
            history: list = []
            if user_id:
                history = get_memory(5, user_id, repo_name)
            history_text = "\n".join(
                f"User: {h['question']}\nAssistant: {h['answer']}" for h in reversed(history)
            )

            # 3. Build prompt
            prompt = (
                "You are RepoTalk, an expert repository intelligence assistant.\n"
                "You explain codebases clearly — covering what each file does, "
                "how functions work, architecture decisions, and anything a developer might wonder about.\n\n"
                f"Repository: {repo_name}\n\n"
                "Relevant Code Context:\n"
                f"{context or 'No indexed content found. The repository may still be indexing.'}\n\n"
                "Recent Conversation:\n"
                f"{history_text or 'No previous conversation.'}\n\n"
                f"User Question: {question}\n\n"
                "Provide a thorough, developer-friendly answer in Markdown. "
                "Cite specific files and functions when relevant."
            )

            # 4. Stream response tokens as JSON-encoded SSE events
            full_answer: list[str] = []
            loop = asyncio.get_event_loop()

            def _blocking_stream() -> list[str]:
                return list(stream_mistral(prompt))

            chunks = await loop.run_in_executor(None, _blocking_stream)

            for chunk in chunks:
                full_answer.append(chunk)
                payload = json.dumps({"token": chunk})
                yield f"data: {payload}\n\n"

            yield "data: [DONE]\n\n"

            # 5. Persist conversation
            if full_answer:
                add_to_memory(question, "".join(full_answer), user_id, repo_name)

        except Exception as exc:
            err_payload = json.dumps({"error": str(exc)})
            yield f"data: {err_payload}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ─── Streaming chat (POST) ────────────────────────────────────────────────────

@router.post("/stream")
async def chat_stream_post(
    req: StreamChatRequest,
    user_id: Optional[int] = Depends(get_optional_user_id),
):
    """POST-based SSE for clients that support it."""
    # Delegate to the same logic as the GET handler
    return await chat_stream_get(req.question, req.repo_name, user_id)


# ─── History ─────────────────────────────────────────────────────────────────

@router.get("/history")
def get_chat_history(
    repo_name: str,
    user_id: int = Depends(get_current_user_id),
):
    """Return conversation history for the given repo."""
    history = get_conversation_history(user_id, repo_name, limit=50)
    return {"repo_name": repo_name, "history": history}


@router.delete("/history")
def delete_chat_history(
    repo_name: str,
    user_id: int = Depends(get_current_user_id),
):
    """Clear conversation history for the given repo."""
    cleared = clear_memory(user_id, repo_name)
    return {"cleared": cleared, "repo_name": repo_name}


# ─── User repos ───────────────────────────────────────────────────────────────

@router.get("/repos")
def list_user_repos(user_id: int = Depends(get_current_user_id)):
    """Return list of repository names the user has indexed."""
    repos = get_user_repos(user_id)
    return {"repos": repos}
