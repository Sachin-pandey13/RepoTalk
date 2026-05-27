from backend.services.database_service import (
    connection,
    cursor
)


def add_to_memory(question, answer):

    cursor.execute(
        """
        INSERT INTO memory (question, answer)
        VALUES (?, ?)
        """,
        (question, answer)
    )

    connection.commit()


def get_memory(limit=5):

    cursor.execute(
        """
        SELECT question, answer
        FROM memory
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cursor.fetchall()

    memory = []

    for row in rows:

        memory.append({
            "question": row[0],
            "answer": row[1]
        })

    return memory