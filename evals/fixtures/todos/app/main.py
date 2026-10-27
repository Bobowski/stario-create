import asyncio

from litewriter import LiteWriter, Tx
from stario import App, Span, serve
from stario.http import same_origin, security_headers

from app.assets import ASSETS
from app.config import Config
from app.features.home.handlers import HomePage
from app.features.todos import data as todos_data
from app.features.todos.handlers import TodosPage


def schema(tx: Tx) -> None:
    todos_data.schema(tx)


async def bootstrap(app: App, span: Span):
    config = Config.from_env()
    async with LiteWriter(config.db_path, schema=schema, claim=30) as db:
        app.use("/", same_origin(), security_headers())
        span.attrs(await ASSETS.attach(app))
        HomePage(config.app_name).register(app)
        TodosPage(db).register(app)
        yield


if __name__ == "__main__":
    asyncio.run(serve(bootstrap))
