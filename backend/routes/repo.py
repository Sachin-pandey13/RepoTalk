"""
backend/routes/repo.py  — Legacy REST endpoints (preserved for backward compatibility).
New code should use /chat/* routes instead.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.repo_service import clone_repository
from backend.services.scanner_service import scan_repository
from backend.services.parser_service import parse_file, parse_repository
from backend.services.embedding_service import index_repository, semantic_search
from backend.services.llm_service import ask_mistral
from backend.services.memory_service import add_to_memory, get_memory
from backend.services.call_graph_service import generate_call_graph
from agents.repository_agent import RepositoryAgent

router = APIRouter()


@router.get("/repo")
def repo_info():
    return {"project": "RepoTalk", "purpose": "Codebase Intelligence System"}


@router.post("/clone")
def clone_repo(repo_url: str):
    return clone_repository(repo_url)


@router.get("/scan")
def scan_repo(repo_name: str):
    return scan_repository(f"workspace/{repo_name}")


@router.get("/parse")
def parse_single_file(file_path: str):
    """Parse a single file (any supported language)."""
    return parse_file(file_path)


@router.get("/parse-repo")
def parse_repo(repo_name: str):
    return parse_repository(f"workspace/{repo_name}")


@router.get("/visualize")
def visualize_repo(repo_name: str):
    from backend.services.visualization_service import generate_dependency_graph
    import os
    repo_path = f"workspace/{repo_name}"
    parsed_result = parse_repository(repo_path)
    os.makedirs("backend/static", exist_ok=True)
    graph_path = generate_dependency_graph(parsed_result["dependency_graph"])
    return {"message": "Dependency graph generated", "graph_file": graph_path}


@router.get("/index-repo")
def index_repo(repo_name: str):
    parsed_result = parse_repository(f"workspace/{repo_name}")
    return index_repository(parsed_result["parsed_files"], repo_name)


@router.get("/search")
def search_repo(repo_name: str, query: str):
    results = semantic_search(query, repo_name, top_k=5)
    return {"repository": repo_name, "query": query, "results": results}


@router.get("/ask")
def ask_repo(repo_name: str, question: str):
    search_results = semantic_search(question, repo_name, top_k=3)
    context = "\n\n".join(r["content"] for r in search_results)
    memory = get_memory(3)
    history = "\n".join(
        f"Q: {m['question']}\nA: {m['answer']}" for m in memory
    )
    prompt = (
        f"You are an expert on the repository: {repo_name}\n\n"
        f"Code context:\n{context}\n\n"
        f"History:\n{history}\n\n"
        f"Question: {question}"
    )
    answer = ask_mistral(prompt)
    add_to_memory(question, answer)
    return {"repository": repo_name, "question": question, "answer": answer}


@router.get("/call-graph")
def visualize_call_graph(repo_name: str):
    parsed = parse_repository(f"workspace/{repo_name}")
    graph_path = generate_call_graph(parsed["parsed_files"])
    return {"message": "Call graph generated", "graph_file": graph_path}


class AgentAskRequest(BaseModel):
    repo_name: str
    question: str
    max_iterations: int = 6


@router.post("/agent/ask")
def agent_ask_post(request: AgentAskRequest):
    agent = RepositoryAgent(
        repo_name=request.repo_name,
        max_iterations=request.max_iterations,
    )
    return agent.run(request.question)


@router.get("/agent/ask")
def agent_ask_get(repo_name: str, question: str, max_iterations: int = 6):
    agent = RepositoryAgent(repo_name=repo_name, max_iterations=max_iterations)
    return agent.run(question)