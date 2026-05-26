from fastapi import FastAPI

from backend.routes.health import router as health_router
from backend.routes.repo import router as repo_router

app = FastAPI(
    title="RepoTalk",
    description="Codebase Intelligence System",
    version="0.1.0"
)

app.include_router(health_router)
app.include_router(repo_router)

@app.get("/")
def home():
    return {
        "message": "Welcome to RepoTalk"
    }