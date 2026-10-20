from dataclasses import dataclass

from litewriter import Tx

SCHEMA = """
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0
);
"""

ITEMS = "SELECT id, title, done FROM todos ORDER BY id"


@dataclass(frozen=True, slots=True)
class Todo:
    id: int
    title: str
    done: bool


def add_todo(tx: Tx, title: str) -> int:
    return tx.value("INSERT INTO todos (title) VALUES (:title) RETURNING id", title=title)


def toggle_done(tx: Tx, todo_id: int) -> None:
    tx.execute("UPDATE todos SET done = 1 - done WHERE id = :id", id=todo_id)
