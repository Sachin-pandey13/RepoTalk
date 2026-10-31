from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.repo_service import clone_repository
from backend.services.scanner_service import scan_repository
from backend.services.parser_service import parse_python_file
from backend.services.parser_service import parse_repository
from backend.services.visualization_service import generate_dependency_graph
from backend.services.embedding_service import (
    index_repository,
    semantic_search
)
from backend.services.llm_service import ask_mistral
from backend.services.memory_service import (
    add_to_memory,
    get_memory
)
from backend.services.call_graph_service import generate_call_graph
from agents.repository_agent import RepositoryAgent


router = APIRouter()


@router.get("/repo")
def repo_info():
    return {
        "project": "RepoTalk",
        "purpose": "Codebase Intelligence System"
    }


@router.post("/clone")
def clone_repo(repo_url: str):

    result = clone_repository(repo_url)

    return result


@router.get("/scan")
def scan_repo(repo_name: str):

    repo_path = f"workspace/{repo_name}"

    result = scan_repository(repo_path)

    return result


@router.get("/parse")
def parse_file(file_path: str):

    result = parse_python_file(file_path)

    return result


@router.get("/parse-repo")
def parse_repo(repo_name: str):

    repo_path = f"workspace/{repo_name}"

    result = parse_repository(repo_path)

    return result


@router.get("/visualize")
def visualize_repo(repo_name: str):

    repo_path = f"workspace/{repo_name}"

    parsed_result = parse_repository(repo_path)

    dependency_graph = parsed_result["dependency_graph"]

    graph_path = generate_dependency_graph(
        dependency_graph
    )

    return {
        "message": "Dependency graph generated successfully",
        "graph_file": graph_path
    }


@router.get("/index-repo")
def index_repo(repo_name: str):

    repo_path = f"workspace/{repo_name}"

    parsed_result = parse_repository(
        repo_path
    )

    parsed_files = parsed_result["parsed_files"]

    result = index_repository(
        parsed_files,
        repo_name
    )

    return result


@router.get("/search")
def search_repo(
    repo_name: str,
    query: str
):

    results = semantic_search(
        query,
        repo_name,
        top_k=5
    )

    return {
        "repository": repo_name,
        "query": query,
        "results": results
    }


@router.get("/ask")
def ask_repo(
    repo_name: str,
    question: str
):

    search_results = semantic_search(
        question,
        repo_name,
        top_k=2
    )

    context = ""

    for result in search_results:

        context += result["content"]
        context += "\n\n"

    # Get previous conversation memory
    memory = get_memory()[-3:]

    conversation_context = ""

    for item in memory:

        conversation_context += f"""
        Previous Question:
        {item['question']}

        Previous Answer:
        {item['answer']}
        """

    # Build intelligent prompt
    prompt = f"""
    You are an AI repository assistant.

    You are answering questions about this repository:
    {repo_name}

    Use the repository context and conversation history
    to answer the question clearly.

    Repository Context:
    {context}

    Conversation History:
    {conversation_context}

    Current Question:
    {question}
    """

    answer = ask_mistral(
        prompt
    )

    # Save current interaction into memory
    add_to_memory(
        question,
        answer
    )

    return {
        "repository": repo_name,
        "question": question,
        "answer": answer
    }


@router.get("/call-graph")
def visualize_call_graph(
    repo_name: str
):

    repo_path = f"workspace/{repo_name}"

    parsed_result = parse_repository(
        repo_path
    )

    parsed_files = parsed_result["parsed_files"]

    graph_path = generate_call_graph(
        parsed_files
    )

    return {
        "message": "Function call graph generated",
        "graph_file": graph_path
    }


class AgentAskRequest(BaseModel):
    repo_name: str
    question: str
    max_iterations: int = 6


@router.post("/agent/ask")
def agent_ask_post(
    request: AgentAskRequest
):

    agent = RepositoryAgent(
        repo_name=request.repo_name,
        max_iterations=request.max_iterations
    )

    result = agent.run(
        request.question
    )

    return result


@router.get("/agent/ask")
def agent_ask_get(
    repo_name: str,
    question: str,
    max_iterations: int = 6
):

    agent = RepositoryAgent(
        repo_name=repo_name,
        max_iterations=max_iterations
    )

    result = agent.run(
        question
    )

    return result