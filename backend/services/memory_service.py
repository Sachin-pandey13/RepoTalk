"""
backend/services/memory_service.py
Conversation history per user + repo, with legacy fallback.
"""
from typing import Optional
from backend.services.database_service import db_cursor


def add_to_memory(
    question: str,
    answer: str,
    user_id: Optional[int] = None,
    repo_name: Optional[str] = None,
) -> None:
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO memory (user_id, repo_name, question, answer)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, repo_name, question, answer),
        )


def get_memory(
    limit: int = 5,
    user_id: Optional[int] = None,
    repo_name: Optional[str] = None,
) -> list[dict]:
    with db_cursor() as cur:
        if user_id and repo_name:
            cur.execute(
                """
                SELECT question, answer FROM memory
                WHERE user_id=? AND repo_name=?
                ORDER BY id DESC LIMIT ?
                """,
                (user_id, repo_name, limit),
            )
        elif user_id:
            cur.execute(
                """
                SELECT question, answer FROM memory
                WHERE user_id=?
                ORDER BY id DESC LIMIT ?
                """,
                (user_id, limit),
            )
        else:
            cur.execute(
                "SELECT question, answer FROM memory ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        rows = cur.fetchall()
        return [{"question": r[0], "answer": r[1]} for r in rows]


def get_conversation_history(
    user_id: int,
    repo_name: str,
    limit: int = 20,
) -> list[dict]:
    """Returns full conversation history ordered oldest-first."""
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT question, answer, created_at FROM memory
            WHERE user_id=? AND repo_name=?
            ORDER BY id ASC LIMIT ?
            """,
            (user_id, repo_name, limit),
        )
        rows = cur.fetchall()
        messages: list[dict] = []
        for r in rows:
            messages.append({"role": "user", "content": r[0]})
            messages.append({"role": "assistant", "content": r[1]})
        return messages


def clear_memory(user_id: int, repo_name: str) -> int:
    """Delete all memory entries for a user + repo. Returns deleted row count."""
    with db_cursor() as cur:
        cur.execute(
            "DELETE FROM memory WHERE user_id=? AND repo_name=?",
            (user_id, repo_name),
        )
        return cur.rowcount