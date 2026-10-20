from litewriter import LiteWriter
from stario import App, Context, Writer
from stario.datastar import SSE, read_signals

from app.features.todos.data import ITEMS, Todo, add_todo, toggle_done
from app.features.todos.urls import ADD_TODO, TODOS, TODOS_LIVE, TOGGLE_TODO
from app.features.todos.views import render


def show_todos(db: LiteWriter):
    async def handler(c: Context, w: Writer) -> None:
        w.html(render([Todo(r[0], r[1], bool(r[2])) for r in db.query(ITEMS)]))

    return handler


def todos_live(db: LiteWriter):
    async def handler(c: Context, w: Writer) -> None:
        sse = SSE(w)
        async with db.watch(ITEMS) as rows:
            async for todos in c.alive(rows):
                sse.patch_elements(render([Todo(r[0], r[1], bool(r[2])) for r in todos]))

    return handler


def add_item(db: LiteWriter):
    async def handler(c: Context, w: Writer) -> None:
        title = str((await read_signals(c.req)).get("title", "")).strip()
        if not title:
            w.empty()
            return
        SSE(w).patch_signals({"title": ""})
        await db.write(add_todo, title)

    return handler


def toggle_item(db: LiteWriter):
    async def handler(c: Context, w: Writer) -> None:
        try:
            todo_id = int(c.match.params["todo_id"])
        except ValueError:
            w.text("todo id must be an integer", status=400)
            return
        if db.one("SELECT id FROM todos WHERE id = :id", id=todo_id) is None:
            w.text("no such todo", status=404)
            return
        w.empty()
        await db.write(toggle_done, todo_id)

    return handler


def register_todos(app: App, db: LiteWriter) -> None:
    app.add(TODOS, show_todos(db))
    app.add(TODOS_LIVE, todos_live(db))
    app.add(ADD_TODO, add_item(db))
    app.add(TOGGLE_TODO, toggle_item(db))
