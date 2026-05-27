from fastapi import APIRouter

from backend.services.repo_service import clone_repository
from backend.services.scanner_service import scan_repository
from backend.services.parser_service import parse_python_file

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