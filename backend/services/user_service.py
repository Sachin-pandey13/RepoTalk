"""
backend/services/user_service.py
CRUD helpers for the users table.
"""
from typing import Optional
from backend.services.database_service import db_cursor


def upsert_user(
    provider: str,
    provider_id: str,
    email: Optional[str] = None,
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    username: Optional[str] = None,
) -> dict:
    """Insert or update a user record and return the full row."""
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (provider, provider_id, email, name, avatar_url, username)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider, provider_id)
            DO UPDATE SET
                email      = excluded.email,
                name       = excluded.name,
                avatar_url = excluded.avatar_url,
                username   = excluded.username
            """,
            (provider, provider_id, email, name, avatar_url, username),
        )
        cur.execute(
            "SELECT * FROM users WHERE provider=? AND provider_id=?",
            (provider, provider_id),
        )
        row = cur.fetchone()
        return dict(row)


def get_user_by_id(user_id: int) -> Optional[dict]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_repos(user_id: int) -> list[dict]:
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM repos WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def upsert_repo(
    user_id: int,
    repo_url: str,
    repo_name: str,
    status: str = "pending",
) -> dict:
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO repos (user_id, repo_url, repo_name, status)
            VALUES (?, ?, ?, ?)
            ON CONFLICT DO NOTHING
            """,
            (user_id, repo_url, repo_name, status),
        )
        cur.execute(
            "SELECT * FROM repos WHERE user_id=? AND repo_url=?",
            (user_id, repo_url),
        )
        row = cur.fetchone()
        return dict(row)


def update_repo_status(
    repo_id: int,
    status: str,
    error_msg: Optional[str] = None,
) -> None:
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE repos
            SET status=?, error_msg=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (status, error_msg, repo_id),
        )
