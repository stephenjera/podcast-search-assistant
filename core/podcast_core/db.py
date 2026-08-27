from collections.abc import Iterator
from contextlib import contextmanager

from pgvector.psycopg import register_vector
from psycopg import Connection, connect

from podcast_core.config import settings


@contextmanager
def get_db_connection() -> Iterator[Connection]:
    with connect(settings.DATABASE_URL) as conn:
        register_vector(conn)
        yield conn
