import os
from git import Repo

WORKSPACE_DIR = "workspace"


def clone_repository(repo_url: str):

    repo_name = repo_url.split("/")[-1].replace(".git", "")
    local_path = os.path.join(WORKSPACE_DIR, repo_name)

    # Prevent duplicate cloning
    if os.path.exists(local_path):
        return {
            "message": "Repository already exists",
            "local_path": local_path
        }

    Repo.clone_from(repo_url, local_path)

    return {
        "message": "Repository cloned successfully",
        "local_path": local_path
    }