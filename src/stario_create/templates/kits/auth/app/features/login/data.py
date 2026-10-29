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
