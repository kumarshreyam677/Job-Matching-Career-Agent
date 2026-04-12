from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import S

pool: ConnectionPool | None = None


def _configure(conn):
    register_vector(conn)


def init():
    global pool
    pool = ConnectionPool(
        S.database_url,
        min_size=1,
        max_size=4,
        kwargs={"row_factory": dict_row, "autocommit": True},
        configure=_configure,
        open=True,
    )


def conn():
    return pool.connection()
