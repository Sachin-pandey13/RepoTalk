import sqlite3


connection = sqlite3.connect(
    "repotalk_memory.db",
    check_same_thread=False
)

cursor = connection.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT,
    answer TEXT
)
""")

connection.commit()