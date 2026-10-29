---
name: stario-login
description: The users table, the login page, sign-up, and logout of a Stario app, with TestClient tests for sign-in, a wrong password, and a protected page. Use with stario-auth when the user asks for accounts, sign up, sign in, or sign out.
---

# Users, login, sign-up, and logout

Skill `stario-auth` holds `app/common/session.py`, the `Config` fields, and the wiring in `bootstrap`. The users table is in SQLite (skill `stario-litewriter`).

## The users table: `app/features/login/data.py`

```python
from litewriter import LiteWriter, Tx
from stario.json import dumps


def schema(tx: Tx) -> None:
    tx.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        " id TEXT PRIMARY KEY, data TEXT NOT NULL CHECK (json_valid(data)),"
        " email TEXT AS (data->>'email') VIRTUAL)"
    )
    tx.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_email ON users(email)")


def get_login(db: LiteWriter, email: str) -> tuple[str, str] | None:
    return db.one("SELECT id, data->>'password' FROM users WHERE email = :email", email=email)


def count_users(db: LiteWriter) -> int:
    return db.value("SELECT count(*) FROM users")


def add_user(tx: Tx, user_id: str, email: str, password_hash: str) -> None:
    tx.execute(
        "INSERT INTO users (id, data) VALUES (:id, :data)",
        id=user_id,
        data=dumps({"email": email, "password": password_hash}),
    )
```

Hash the password before `db.write`, never inside the write function: the hash would hold the writer's whole batch. A sign-up with a taken email raises `apsw.ConstraintError` from `db.write`. Catch it and send "That email is already registered." to the tab.

## The login page: `app/features/login/`

Login is a static page. Its submit is a command with no stream. Checking the password is a read, so it is part of validation. The reply is the cookie and `navigate`, or the error in a signal. The reply is never HTML.

```python
# urls.py
from stario import Route

LOGIN = Route("GET /login")
LOGIN_POST = Route("POST /login")
LOGOUT = Route("POST /logout")
```

```python
# views.py
from stario import h
from stario.datastar import at, data
from stario.markup import HtmlElement

from app.common.shell import page
from app.features.login.urls import LOGIN_POST


def render() -> HtmlElement:
    return page(
        "Sign in",
        h.Main(
            {"id": "login"},
            data.signals({"email": "", "password": "", "_error": ""}, if_missing=True),
            h.Form(
                data.on("submit", at.post(LOGIN_POST.href()), prevent=True),
                h.Label(
                    "Email",
                    h.Input(
                        {"type": "email", "required": True, "autocomplete": "username"},
                        data.bind("email"),
                    ),
                ),
                h.Label(
                    "Password",
                    h.Input(
                        {"type": "password", "required": True, "autocomplete": "current-password"},
                        data.bind("password"),
                    ),
                ),
                h.P({"role": "alert"}, data.show("$_error"), data.text("$_error")),
                h.Button({"type": "submit"}, "Sign in"),
            ),
        ),
    )
```

```python
# handlers.py
import asyncio
from dataclasses import dataclass

from litewriter import LiteWriter
from stario import App, Context, Writer
from stario.datastar import SSE, read_signals

from app.common.session import Session, check_password
from app.features.home.urls import HOME
from app.features.login.data import get_login
from app.features.login.urls import LOGIN, LOGIN_POST, LOGOUT
from app.features.login.views import render


@dataclass(frozen=True, slots=True)
class LoginPage:
    db: LiteWriter
    session: Session

    def register(self, app: App) -> None:
        app.add(LOGIN, self.show)
        app.add(LOGIN_POST, self.submit)
        app.add(LOGOUT, self.logout)

    async def show(self, c: Context, w: Writer) -> None:
        if c.state.get("user"):
            w.redirect(HOME.href(), status=303)
            return
        w.html(render())

    async def submit(self, c: Context, w: Writer) -> None:
        signals = await read_signals(c.req)
        email = str(signals.get("email", "")).strip().lower()
        password = str(signals.get("password", ""))
        login = get_login(self.db, email)
        if login is None or not await asyncio.to_thread(check_password, password, login[1]):
            SSE(w).patch_signals({"password": "", "_error": "Wrong email or password."})
            return
        self.session.issue(w, login[0])
        SSE(w).navigate(HOME.href())

    async def logout(self, c: Context, w: Writer) -> None:
        self.session.clear(w)
        SSE(w).navigate(LOGIN.href())
```

`Set-Cookie` goes out with the first write, so `issue` and `clear` come before `navigate`. A sign-up page has the same shape: validate, `hash_password` in `to_thread`, `await db.write(add_user, str(uuid.uuid7()), email, password_hash)`, issue, navigate.

A logout button on any page: `h.Button({"type": "button"}, data.on("click", at.post(LOGOUT.href())), "Sign out")`.

## Tests

Prove login with `TestClient`. Do not open a browser for a sign-in or a redirect.

```python
# tests/conftest.py
import pytest
from stario.testing import TestClient

from app.features.login.urls import LOGIN_POST
from app.main import bootstrap


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SESSION_SECRET", "test-secret-test-secret-test-secret-test")
    monkeypatch.setenv("APP_DEV", "1")
    monkeypatch.setenv("ADMIN_EMAIL", "ada@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "correct-horse")
    async with TestClient(bootstrap, request_timeout=5) as c:
        yield c


async def login(client, email="ada@example.com", password="correct-horse") -> None:
    r = await client.post(LOGIN_POST.href(), json={"email": email, "password": password})
    assert "window.location" in r.text
```

```python
# tests/test_login.py
from app.features.board.urls import BOARD
from app.features.login.urls import LOGIN, LOGIN_POST, LOGOUT
from tests.conftest import login


async def test_protected_page_redirects_to_login(client):
    r = await client.get(BOARD.href(), follow_redirects=False)
    assert r.status_code == 303
    assert r.headers.get("location") == LOGIN.href()


async def test_wrong_password_sets_the_error_signal(client):
    r = await client.post(LOGIN_POST.href(), json={"email": "ada@example.com", "password": "no"})
    assert "Wrong email or password" in r.text
    assert "window.location" not in r.text


async def test_login_then_logout(client):
    await login(client)
    assert (await client.get(BOARD.href())).status_code == 200
    await client.post(LOGOUT.href())
    assert (await client.get(BOARD.href(), follow_redirects=False)).status_code == 303
```

`TestClient` keeps a cookie jar, so `login` makes the next `GET` signed in. A stream under `/app` that is opened signed out replies `navigate`, not `303`: send `headers={"datastar-request": "true"}` and assert `"window.location" in r.text`.

