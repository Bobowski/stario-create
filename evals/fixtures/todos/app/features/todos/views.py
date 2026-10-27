from stario import h
from stario.datastar import at, data
from stario.markup import HtmlElement

from app.common.shell import page
from app.features.todos.data import Todo
from app.features.todos.urls import ADD_TODO, TODOS_LIVE, TOGGLE_TODO


def render(items: list[Todo]) -> HtmlElement:
    return page(
        "Todos",
        h.Main(
            {"id": "todos"},
            data.signals({"title": ""}, if_missing=True),
            data.init(at.get(TODOS_LIVE.href(), retry="always")),
            h.H1("Todos"),
            h.Form(
                data.on("submit", at.post(ADD_TODO.href()), prevent=True),
                data.indicator("_adding"),
                h.Input(
                    {
                        "type": "text",
                        "placeholder": "What needs doing?",
                        "autocomplete": "off",
                        "required": True,
                    },
                    data.bind("title"),
                ),
                h.Button({"type": "submit"}, data.attr("disabled", "$_adding"), "Add"),
            ),
            h.Ul(*[item(t) for t in items]) if items else h.P("Nothing to do yet."),
        ),
    )


def item(t: Todo) -> HtmlElement:
    return h.Li(
        h.Label(
            h.Input(
                {"type": "checkbox", "checked": bool(t.done)},
                data.on("click", at.post(TOGGLE_TODO.href(t.id)), prevent=True),
            ),
            h.S(t.title) if t.done else t.title,
        )
    )
