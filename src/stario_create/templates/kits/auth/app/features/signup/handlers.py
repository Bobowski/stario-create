import asyncio
import uuid
from dataclasses import dataclass

import apsw
from litewriter import LiteWriter
from stario import App, Context, Writer
from stario.datastar import SSE, read_signals

from app.common.session import Session, hash_password
from app.features.home.urls import HOME
from app.features.login.data import add_user
from app.features.signup.urls import SIGNUP, SIGNUP_POST
from app.features.signup.views import render


@dataclass(frozen=True, slots=True)
class SignupPage:
    db: LiteWriter
    session: Session

    def register(self, app: App) -> None:
        app.add(SIGNUP, self.show)
        app.add(SIGNUP_POST, self.submit)

    async def show(self, c: Context, w: Writer) -> None:
        w.html(render())

    async def submit(self, c: Context, w: Writer) -> None:
        signals = await read_signals(c.req)
        email = str(signals.get("email", "")).strip().lower()
        password = str(signals.get("password", ""))
        if "@" not in email or len(email) > 200:
            w.text("email must be an address", status=400)
            return
        if len(password) < 12:
            SSE(w).patch_signals({"_error": "Use 12 or more characters."})
            return
        user_id = str(uuid.uuid7())
        password_hash = await asyncio.to_thread(hash_password, password)
        try:
            await self.db.write(add_user, user_id, email, password_hash)
        except apsw.ConstraintError:
            SSE(w).patch_signals({"password": "", "_error": "That email is already registered."})
            return
        self.session.issue(w, user_id)
        SSE(w).navigate(HOME.href())
