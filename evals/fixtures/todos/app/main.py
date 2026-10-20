import asyncio

from litewriter import LiteWriter
from stario import App, Span, serve
from stario.http import same_origin, security_headers

from app.assets import ASSETS
from app.config import Config
from app.features.home.handlers import register_home
from app.features.todos import data as todos_data
from app.features.todos.handlers import register_todos


async def bootstrap(app: App, span: Span):
    config = Config.from_env()
    async with LiteWriter(config.db_path, schema=todos_data.SCHEMA, claim=30) as db:
        app.use("/", same_origin(), security_headers())
        span.attrs(await ASSETS.attach(app))
        register_home(app, config.app_name)
        register_todos(app, db)
        yield


if __name__ == "__main__":
    asyncio.run(serve(bootstrap))
