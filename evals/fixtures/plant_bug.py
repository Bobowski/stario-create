from pathlib import Path

def sub(path, old, new):
    p = Path(path); t = p.read_text()
    assert t.count(old) == 1, (path, old[:60])
    p.write_text(t.replace(old, new))

h = "app/features/todos/handlers.py"
sub(h, "from stario import App, Context, Writer\n", "from stario import App, Context, Relay, Writer\n")
sub(h, "from app.features.todos.views import render\n", 'from app.features.todos.views import render\n\nCHANGED = "todos.changed"\n')
sub(h, "    db: LiteWriter\n", "    db: LiteWriter\n    relay: Relay[str]\n")
sub(h, '''        sse = SSE(w)
        async with self.db.watch(ITEMS, Todo) as rows:
            async for todos in c.alive(rows):
                sse.patch_elements(render(todos))
''', '''        async with self.relay.subscribe(CHANGED, latest=True) as events:
            sse = SSE(w)
            sse.patch_elements(render(list_todos(self.db)))
            async for _ in c.alive(events):
                sse.patch_elements(render(list_todos(self.db)))
''')
sub(h, "        w.empty()\n        await self.db.write(toggle_done, int(todo_id))\n",
       '        w.empty()\n        await self.db.write(toggle_done, int(todo_id))\n        self.relay.publish(CHANGED, "toggle")\n')
sub(h, "from app.features.todos.data import ITEMS, Todo, add_todo, get_todo, list_todos, toggle_done\n",
       "from app.features.todos.data import add_todo, get_todo, list_todos, toggle_done\n")
m = "app/main.py"
sub(m, "from stario import App, Span, serve", "from stario import App, Relay, Span, serve")
sub(m, "TodosPage(db).register(app)", "TodosPage(db, Relay()).register(app)")
p = Path("tests/test_todos.py"); t = p.read_text()
a = t.index("async def test_add_repaints_the_stream"); b = t.index("async def test_toggle_repaints_the_stream")
p.write_text(t[:a] + t[b:])
print("planted")
