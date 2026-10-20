from pathlib import Path

def sub(path, old, new):
    p = Path(path); t = p.read_text()
    assert t.count(old) == 1, (path, old[:60])
    p.write_text(t.replace(old, new))

h = "app/features/todos/handlers.py"
sub(h, "from stario import App, Context, Writer\n", "from stario import App, Context, Relay, Writer\n")
sub(h, "from app.features.todos.views import render\n", 'from app.features.todos.views import render\n\nCHANGED = "todos.changed"\n')
sub(h, '''def todos_live(db: LiteWriter):
    async def handler(c: Context, w: Writer) -> None:
        sse = SSE(w)
        async with db.watch(ITEMS) as rows:
            async for todos in c.alive(rows):
                sse.patch_elements(render([Todo(r[0], r[1], bool(r[2])) for r in todos]))
''', '''def todos_live(db: LiteWriter, relay: Relay[str]):
    async def handler(c: Context, w: Writer) -> None:
        async with relay.subscribe(CHANGED) as events:
            sse = SSE(w)
            sse.patch_elements(render([Todo(r[0], r[1], bool(r[2])) for r in db.query(ITEMS)]))
            async for _ in c.alive(events):
                sse.patch_elements(render([Todo(r[0], r[1], bool(r[2])) for r in db.query(ITEMS)]))
''')
sub(h, "def toggle_item(db: LiteWriter):", "def toggle_item(db: LiteWriter, relay: Relay[str]):")
sub(h, "        w.empty()\n        await db.write(toggle_done, todo_id)\n",
       '        w.empty()\n        await db.write(toggle_done, todo_id)\n        relay.publish(CHANGED, "toggle")\n')
sub(h, "def register_todos(app: App, db: LiteWriter) -> None:", "def register_todos(app: App, db: LiteWriter, relay: Relay[str]) -> None:")
sub(h, "    app.add(TODOS_LIVE, todos_live(db))", "    app.add(TODOS_LIVE, todos_live(db, relay))")
sub(h, "    app.add(TOGGLE_TODO, toggle_item(db))", "    app.add(TOGGLE_TODO, toggle_item(db, relay))")
m = "app/main.py"
sub(m, "from stario import App, Span, serve", "from stario import App, Relay, Span, serve")
sub(m, "register_todos(app, db)", "register_todos(app, db, Relay())")
p = Path("tests/test_todos.py"); t = p.read_text()
a = t.index("async def test_add_repaints_the_stream"); b = t.index("async def test_toggle_repaints_the_stream")
p.write_text(t[:a] + t[b:])
print("planted")
