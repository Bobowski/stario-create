from stario import h
from stario.datastar import ModuleScript, data
from stario.markup import HtmlElement, SafeString, baked, classes

from app.assets import DATASTAR_JS, SCRIPTS, STYLE_CSS

# The one inline script: it sets the theme before the first paint.
RESTORE_THEME = SafeString(
    "document.documentElement.dataset.theme = localStorage.getItem('theme')"
    " || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')"
)


@baked
def page(title: str, body: HtmlElement) -> HtmlElement:
    return h.HtmlDocument(
        {"lang": "en", "data-theme": "light"},
        data.preserve_attr("data-theme"),
        h.Head(
            h.Meta({"charset": "utf-8"}),
            h.Meta({"name": "viewport", "content": "width=device-width, initial-scale=1"}),
            h.Title(title),
            h.Script(RESTORE_THEME),
            h.Link({"rel": "stylesheet", "href": STYLE_CSS}),
            *[h.Script({"src": src, "defer": True}) for src in SCRIPTS],
            ModuleScript(DATASTAR_JS),
        ),
        h.Body(
            classes("min-h-screen", "bg-base-100", "text-base-content"),
            body,
            h.Div(
                classes("toast", "toast-end"),
                data.show("$_toast"),
                h.Output(
                    classes("alert", "alert-info"),
                    {"id": "toast", "role": "status"},
                    data.signals({"_toast": ""}, if_missing=True),
                    data.text("$_toast"),
                    data.effect("$_toast && setTimeout(() => $_toast = '', 4000)"),
                ),
            ),
        ),
    )
