from dataclasses import dataclass

from litewriter import LiteWriter
from stario import App, Context, Writer
from stario.datastar import SSE, read_signals

from app.features.todos.data import ITEMS, Todo, add_todo, get_todo, list_todos, toggle_done
from app.features.todos.urls import ADD_TODO, TODOS, TODOS_LIVE, TOGGLE_TODO
from app.features.todos.views import render


@dataclass(frozen=True, slots=True)
class TodosPage:
    db: LiteWriter

    def register(self, app: App) -> None:
        app.add(TODOS, self.show)
        app.add(TODOS_LIVE, self.live)
        app.add(ADD_TODO, self.add)
        app.add(TOGGLE_TODO, self.toggle)

    async def show(self, c: Context, w: Writer) -> None:
        w.html(render(list_todos(self.db)))

    async def live(self, c: Context, w: Writer) -> None:
        sse = SSE(w)
        async with self.db.watch(ITEMS, Todo) as rows:
            async for todos in c.alive(rows):
                sse.patch_elements(render(todos))

    async def add(self, c: Context, w: Writer) -> None:
        title = str((await read_signals(c.req)).get("title", "")).strip()
        if not title or len(title) > 200:
            w.text("title must be 1 to 200 characters", status=400)
            return
        SSE(w).patch_signals({"title": ""})
        await self.db.write(add_todo, title)

    async def toggle(self, c: Context, w: Writer) -> None:
        todo_id = c.match.params["todo_id"]
        if not todo_id.isdecimal() or get_todo(self.db, int(todo_id)) is None:
            w.text("no such todo", status=404)
            return
        w.empty()
        await self.db.write(toggle_done, int(todo_id))
