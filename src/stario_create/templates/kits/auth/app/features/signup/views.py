from stario import h
from stario.datastar import at, data
from stario.markup import HtmlElement

from app.common.shell import page
from app.features.login.urls import LOGIN
from app.features.signup.urls import SIGNUP_POST


def render() -> HtmlElement:
    return page(
        "Create an account",
        h.Main(
            {"id": "signup"},
            data.signals({"email": "", "password": "", "_error": ""}, if_missing=True),
            h.H1("Create an account"),
            h.Form(
                data.on("submit", at.post(SIGNUP_POST.href()), prevent=True),
                data.indicator("_sending"),
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
                        {
                            "type": "password",
                            "required": True,
                            "minlength": 12,
                            "autocomplete": "new-password",
                        },
                        data.bind("password"),
                    ),
                ),
                h.P({"role": "alert"}, data.show("$_error"), data.text("$_error")),
                h.Button({"type": "submit"}, data.attr("disabled", "$_sending"), "Create account"),
            ),
            h.P(h.A({"href": LOGIN.href()}, "Sign in instead")),
        ),
    )
