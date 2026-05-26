from fastapi import APIRouter

router = APIRouter()

@router.get("/repo")
def repo_info():
    return {
        "project": "RepoTalk",
        "purpose": "Codebase Intelligence System"
    }