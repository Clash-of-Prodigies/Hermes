import os
import json
from dotenv import load_dotenv
from psycopg import Connection, connect as pg_connect
from psycopg.rows import dict_row
from psycopg.errors import UniqueViolation, OperationalError
from typing import Optional, Dict, Any
load_dotenv()

# ---- Message Schemas ----
class MessageCreate():
    def __init__(self, **kwargs):
        self.channel: str = kwargs.get("channel", "email")
        self.to: str = kwargs.get("to", "")
        self.template: str = kwargs.get("template", "")
        self.subject: str = kwargs.get("subject", "")
        self.locale: Optional[str] = kwargs.get("locale", "en")
        self.data: Dict[str, Any] = kwargs.get("data", {})
        self.idempotency_key: Optional[str] = kwargs.get("idempotency_key")

        if not self.to: raise ValueError("Recipient 'to' is required.")
        if not self.template: raise ValueError("Template is required.")

class MessageResponse():
    def __init__(self, **kwargs):
        self.id: int = kwargs.get("id", 0)
        self.channel: str = kwargs.get("channel", "")
        self.to: str = kwargs.get("to_address", "")
        self.template: str = kwargs.get("template", "")
        self.status: str = kwargs.get("status", "")
        self.idempotency_key: Optional[str] = kwargs.get("idempotency_key")

    def asdict(self):
        return {
            "id": self.id,
            "channel": self.channel,
            "to": self.to,
            "template": self.template,
            "status": self.status,
            "idempotency_key": self.idempotency_key,
        }


# ---- Database operations ----
def get_connection() -> Connection:
    """
    Establish and return a new database connection using environment variables.
    """
    db_host, db_port, db_name, db_user, db_password = environmentals(
        "DB_HOST,DB_PORT,DB_NAME,DB_USER,DB_PASSWORD"
    ).split(",")

    try:
        conn = pg_connect(
        host=db_host,
        port=int(db_port),
        dbname=db_name,
        user=db_user,
        password=db_password,
        )
    except OperationalError as e:
        raise ConnectionError(f"Failed to connect to the database: {e}")
    return conn

def create_message(conn: Connection, payload: MessageCreate):
    """
    Insert a new message row, honoring idempotency_key.
    Returns the existing row if the key already exists.
    """
    row = None
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO messages (channel, to_address, subject, template, locale, data, status, idempotency_key)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, 'queued', %s)
                RETURNING *;
                """,
                (
                    payload.channel,
                    payload.to,
                    payload.subject,
                    payload.template,
                    payload.locale,
                    json.dumps(payload.data),
                    payload.idempotency_key,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return row
    except UniqueViolation:
        conn.rollback()
        if payload.idempotency_key:
            existing = get_message_by_idempotency(conn, payload.idempotency_key)
            if existing: return existing
        raise


def get_message_by_idempotency(conn: Connection, key: str):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM messages WHERE idempotency_key = %s;", (key,)
        )
        return cur.fetchone()


def get_next_queued_message(conn: Connection):
    """
    Use FOR UPDATE SKIP LOCKED so multiple workers can cooperate safely.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT * FROM messages
            WHERE status = 'queued'
            ORDER BY created_at
            FOR UPDATE SKIP LOCKED
            LIMIT 1;
            """
        )
        row = cur.fetchone()
        if not row:
            return None

        # mark sending
        cur.execute(
            """
            UPDATE messages
            SET status = 'sending', updated_at = now()
            WHERE id = %s;
            """,
            (row["id"],),
        )
        cur.execute("COMMIT;")
        # we return row in 'queued' state, but we know it is now 'sending' in DB
        row["status"] = "sending"
        return row


def mark_sent(conn: Connection, msg_id: int):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            UPDATE messages
            SET status = 'sent', last_error = NULL, updated_at = now()
            WHERE id = %s;
            """,
            (msg_id,),
        )
    conn.commit()


def increment_attempts(conn: Connection, msg_id: int, error: str):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            UPDATE messages
            SET attempts = attempts + 1,
                last_error = %s,
                updated_at = now()
            WHERE id = %s
            RETURNING attempts;
            """,
            (error, msg_id),
        )
        row = cur.fetchone()
    conn.commit()
    return row["attempts"] if row else 0


def mark_failed(conn: Connection, msg_id: int, error: str):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            UPDATE messages
            SET status = 'failed',
                last_error = %s,
                updated_at = now()
            WHERE id = %s;
            """,
            (error, msg_id),
        )
    conn.commit()


def should_give_up(attempts: int) -> bool:
    return attempts >= int(environmentals("MESSAGE_MAX_ATTEMPTS", "3"))

def health_check() -> bool:
    """
    Simple health check to verify that required environment variables are set.
    """
    required_vars = [
        "EMAIL_SMTP_HOST",
        "EMAIL_SMTP_PORT",
        "EMAIL_USER",
        "EMAIL_APP_PASSWORD",
        "MESSAGE_MAX_ATTEMPTS",
    ]
    for var in required_vars:
        if not os.getenv(var):
            raise EnvironmentError(f"Environment variable {var} is not set.")
    return True

def environmentals(param: str, default: str = "", delimiter: str = ",") -> str:
    """
    Fetch environment variables, supporting multiple variables separated by a delimiter.

    Args:
        param (str): The environment variable name(s), separated by the delimiter if multiple.
        default (str): The default value(s) to use if the environment variable is not set.
                       If multiple, use the same delimiter as for `param`.
        delimiter (str): The delimiter used to separate multiple variable names and defaults.

    Returns:
        str: The value(s) of the environment variable(s) or the default(s),
             joined by the delimiter if multiple.
    """

    params = [p.strip() for p in param.split(delimiter)]
    defaults = [d.strip() for d in default.split(delimiter)] if default is not None else []

    if len(defaults) < len(params):
        defaults.extend([""] * (len(params) - len(defaults)))

    values = []
    for name, d in zip(params, defaults):
        env_value = os.getenv(name, d)
        values.append(env_value)

    return delimiter.join(values)

def bot_commands(command_name: str, command_payload: dict) -> MessageCreate:
    if command_name == "/start":
        command_payload["template"] = "welcome"
        command_payload["subject"] = "Welcome!"
        command_payload["data"] = {
            "username": "Benjamin",
            "role": "admin",
        }
    elif command_name == "/verify":
        command_payload["template"] = "welcome"
        command_payload["subject"] = "Welcome!"
        # store chat_id later
    else:
        command_payload["template"] = "default"
        command_payload["subject"] = "Notification"

    return MessageCreate(
        channel="telegram",
        to=command_payload["chat_id"],
        template=command_payload.get("template", "default"),
        subject=command_payload.get("subject", "Welcome"),
        data=command_payload.get("data", {}),
    )