---
name: stario-auth
description: User identity in a Stario app - a signed session cookie, middleware that puts the user on c.state, protected pages, and rows that belong to one user. Use when the user asks for login, sign in, accounts, sessions, "who is the user", per-user data, or a page only some users can open. Load stario-login with it for the users table, the login page, sign-up, logout, and the tests.
---

# Sessions and protected pages

Read `AGENTS.md` first. User identity lives in a signed cookie, never in a signal or a URL. Stario ships `set_cookie` and `delete_cookie`, `same_origin()`, and a per-request `c.state` dict. It ships no session store. The code below is the whole default. Copy it; do not import a session library. Skill `stario-login` adds the users table and the login page.

## `app/common/session.py`

One frozen dataclass. It signs, verifies, issues, and clears the cookie, and it gives two middlewares.

```python
import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

from stario import Context, Handler, Middleware, Writer
from stario.cookies import delete_cookie, set_cookie
from stario.datastar import SSE


@dataclass(frozen=True, slots=True)
class Session:
    secret: bytes
    cookie: str = "session"
    max_age: int = 60 * 60 * 24 * 14
    secure: bool = True

    def sign(self, body: str) -> str:
        digest = hmac.new(self.secret, body.encode(), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode()

    def issue(self, w: Writer, user_id: str) -> None:
        body = f"{user_id}.{int(time.time()) + self.max_age}"
        set_cookie(
            w,
            self.cookie,
            f"{body}.{self.sign(body)}",
            max_age=self.max_age,
            httponly=True,
            secure=self.secure,
            samesite="lax",
        )

    def clear(self, w: Writer) -> None:
        delete_cookie(w, self.cookie, httponly=True, secure=self.secure, samesite="lax")

    def user_id(self, c: Context) -> str | None:
        body, _, sig = c.req.cookies.get(self.cookie, "").rpartition(".")
        user_id, _, exp = body.rpartition(".")
        if not user_id or not exp.isdecimal() or int(exp) < time.time():
            return None
        return user_id if hmac.compare_digest(self.sign(body), sig) else None

    def attach(self) -> Middleware:
        """Every request gets c.state["user"]: the user id or None."""

        def middleware(inner: Handler) -> Handler:
            async def handler(c: Context, w: Writer) -> None:
                c.state["user"] = self.user_id(c)
                await inner(c, w)

            return handler

        return middleware

    def require(self, login_url: str) -> Middleware:
        """A page for signed-in users. A page load redirects. A Datastar action navigates."""

        def middleware(inner: Handler) -> Handler:
            async def handler(c: Context, w: Writer) -> None:
                if c.state.get("user") is None:
                    if c.req.headers.get("datastar-request"):
                        SSE(w).navigate(login_url)
                    else:
                        w.redirect(login_url, status=303)
                    return
                await inner(c, w)

            return handler

        return middleware


def hash_password(password: str, salt: bytes | None = None) -> str:
    """About 30 ms of CPU. Call it through asyncio.to_thread from a handler."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def check_password(password: str, stored: str) -> bool:
    salt_b64, _, _ = stored.partition("$")
    return hmac.compare_digest(hash_password(password, base64.b64decode(salt_b64)), stored)
```

`c.state["user"]` is the user id as a string. A handler that needs more reads the user row with that id.

scrypt takes about 30 ms of CPU. On the loop, every other request waits for it. Thus a handler calls `await asyncio.to_thread(check_password, ...)`. `to_thread` uses the loop's thread pool, so a call costs about 20 µs more than a direct call.

## `Config`

Add three fields to the scaffold's `Config` and read them in `from_env`:

```python
secret = os.environ.get("SESSION_SECRET", "")
if len(secret) < 32:
    raise RuntimeError("Set SESSION_SECRET to 32+ random characters.")
admin_email = os.environ.get("ADMIN_EMAIL", "")
admin_password = os.environ.get("ADMIN_PASSWORD", "")
if admin_email and len(admin_password) < 12:
    raise RuntimeError("ADMIN_EMAIL is set: set ADMIN_PASSWORD to 12+ characters.")
# session_secret=secret.encode(), dev=os.environ.get("APP_DEV") == "1",
# admin_email=admin_email, admin_password=admin_password
```

Generate a secret: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. `APP_DEV=1` allows the cookie over plain HTTP on localhost. Do not set it in production. The app does not start with an admin email and no password.

## Wire it in `bootstrap`

```python
async def bootstrap(app: App, span: Span):
    config = Config.from_env()
    async with LiteWriter(config.db_path, schema=schema, claim=30) as db:
        if config.admin_email and login_data.count_users(db) == 0:
            password_hash = await asyncio.to_thread(hash_password, config.admin_password)
            await db.write(
                login_data.add_user, str(uuid.uuid7()), config.admin_email, password_hash
            )
        session = Session(config.session_secret, secure=not config.dev)
        app.use("/", same_origin(), security_headers(), session.attach())
        app.use("/app", session.require(LOGIN.href()))
        span.attrs(await ASSETS.attach(app))
        LoginPage(db, session).register(app)  # skill stario-login
        BoardPage(db, Relay[dict]()).register(app)  # BOARD = Route("GET /app/board")
        yield
```

- Protected pages share one URL prefix, `/app`. Public pages (`/`, `/login`) stay outside it. One `app.use` protects the prefix, including its 404 and 405 answers.
- `same_origin()` must stay before the session middleware. It answers 403 to a `POST`, `PUT`, `PATCH`, or `DELETE` that another site sent. With the `samesite="lax"` cookie, no other page can forge a command.
- `app.use("/", ...)` runs before every route, so `c.state["user"]` is always set.
- One protected page outside the prefix passes `middleware=[session.require(LOGIN.href())]` to `app.add`.

### Accounts in an app that already has pages

- Keep the URLs. Links and bookmarks point at them. Protect a page where it is: `app.use("/todos", session.require(LOGIN.href()))` covers `/todos` and every route below it. Use the `/app` prefix only for new apps.
- Ask the developer what happens to rows that exist before accounts: give them to the seed user, or delete them. If you cannot ask, keep the rows and write the open choice in `## This app`.
- A table whose rows belong to a user gets a real `user_id` column with an index. Every read, stream, and command filters by `c.state["user"]`. A command checks that the row belongs to the user before it changes it (404 when it does not).

## Rules

- The cookie holds the user id and an expiry, signed. It holds no password, no role, no row.
- `httponly=True` always. `secure=True` outside local development. `samesite="lax"`.
- Passwords are hashed with `scrypt` in `asyncio.to_thread`. Never stored in clear, logged, or put in a span attribute.
- A protected page uses `require`. A handler never checks the cookie itself.
- A command that acts for a user reads `c.state["user"]`, not a signal or a path parameter.
- Logout is a `POST`. A `GET` that changes state is a bug.
- A session lasts `max_age` and cannot be revoked one at a time. When the app needs "sign out everywhere", add a `session_version` to the user `data` and to the cookie body, and compare them in `user_id`.
