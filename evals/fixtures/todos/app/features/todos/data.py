from dataclasses import dataclass

from litewriter import LiteWriter, Tx
from stario.json import dumps

COLUMNS = {
    "title": "TEXT AS (data->>'title')",
    "done": "INTEGER AS (data->>'done')",
}

ITEMS = "SELECT id, title, done FROM todos ORDER BY id"


@dataclass(frozen=True, slots=True)
class Todo:
    id: int
    title: str
    done: int


def schema(tx: Tx) -> None:
    tx.execute(
        "CREATE TABLE IF NOT EXISTS todos ("
        " id INTEGER PRIMARY KEY, data TEXT NOT NULL CHECK (json_valid(data)))"
    )
    have = {row[0] for row in tx.query("SELECT name FROM pragma_table_xinfo('todos')")}
    for name, column in COLUMNS.items():
        if name not in have:
            tx.execute(f"ALTER TABLE todos ADD COLUMN {name} {column} VIRTUAL")


def list_todos(db: LiteWriter) -> list[Todo]:
    return db.query(ITEMS, Todo)


def get_todo(db: LiteWriter, todo_id: int) -> Todo | None:
    return db.one("SELECT id, title, done FROM todos WHERE id = :id", Todo, id=todo_id)


def add_todo(tx: Tx, title: str) -> int:
    return tx.value(
        "INSERT INTO todos (data) VALUES (:data) RETURNING id",
        data=dumps({"title": title, "done": False}),
    )


def toggle_done(tx: Tx, todo_id: int) -> None:
    tx.execute(
        "UPDATE todos SET data = json_set(data, '$.done', json(iif(done, 'false', 'true')))"
        " WHERE id = :id",
        id=todo_id,
    )
