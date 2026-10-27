from app.features.todos.urls import ADD_TODO, TODOS, TODOS_LIVE, TOGGLE_TODO


async def test_todos_loads(client):
    r = await client.get(TODOS.href())
    assert r.status_code == 200
    assert 'id="todos"' in r.text


async def test_add_repaints_the_stream(client):
    async with client.stream("GET", TODOS_LIVE.href()) as live:
        events = live.iter_events()
        assert 'id="todos"' in (await anext(events))["data"]
        r = await client.post(ADD_TODO.href(), json={"title": "Buy milk"})
        assert r.status_code == 200
        assert "Buy milk" in (await anext(events))["data"]


async def test_toggle_repaints_the_stream(client):
    await client.post(ADD_TODO.href(), json={"title": "Buy milk"})
    async with client.stream("GET", TODOS_LIVE.href()) as live:
        events = live.iter_events()
        first = (await anext(events))["data"]
        assert "Buy milk" in first
        assert "checked" not in first
        r = await client.post(TOGGLE_TODO.href(1))
        assert r.status_code == 204
        assert "checked" in (await anext(events))["data"]


async def test_add_empty_title_is_rejected(client):
    r = await client.post(ADD_TODO.href(), json={"title": "   "})
    assert r.status_code == 400


async def test_toggle_unknown_todo_returns_404(client):
    assert (await client.post(TOGGLE_TODO.href(999))).status_code == 404
    assert (await client.post(TOGGLE_TODO.href("x"))).status_code == 404
