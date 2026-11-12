"""Acceso a datos. Las consultas usan ? como marcador en ambos motores."""
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

DB_DIR = Path(__file__).resolve().parent.parent / "db"


def split_sql(script):
    """Separa un script en sentencias (sin comentarios de linea)."""
    script = re.sub(r"--[^\n]*", "", script)
    return [s.strip() for s in script.split(";") if s.strip()]


class Database:
    schema_file = ""

    def query_one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def init_schema(self):
        self.run_script((DB_DIR / self.schema_file).read_text(encoding="utf-8"))


class SQLiteDB(Database):
    schema_file = "schema.sqlite.sql"

    def __init__(self, path=":memory:"):
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.RLock()

    def query(self, sql, params=()):
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def execute(self, sql, params=()):
        with self._lock:
            return self._conn.execute(sql, params).lastrowid

    def run_script(self, script):
        with self._lock:
            self._conn.executescript(script)

    @contextmanager
    def transaction(self):
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                yield
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise


class MySQLDB(Database):
    schema_file = "schema.mysql.sql"

    def __init__(self, host, port, user, password, name):
        self._cfg = dict(host=host, port=port, user=user, password=password,
                         database=name, charset="utf8mb4", autocommit=True)
        self._local = threading.local()

    def _conn(self):
        import pymysql
        import pymysql.cursors
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **self._cfg)
            self._local.conn = conn
        else:
            conn.ping(reconnect=True)
        return conn

    @staticmethod
    def _clean(row):
        return {k: str(v) if isinstance(v, (datetime, date)) else v for k, v in row.items()}

    def query(self, sql, params=()):
        with self._conn().cursor() as cur:
            cur.execute(sql.replace("?", "%s"), params)
            return [self._clean(r) for r in cur.fetchall()]

    def execute(self, sql, params=()):
        with self._conn().cursor() as cur:
            cur.execute(sql.replace("?", "%s"), params)
            return cur.lastrowid

    def run_script(self, script):
        for statement in split_sql(script):
            self.execute(statement)

    @contextmanager
    def transaction(self):
        conn = self._conn()
        conn.begin()
        try:
            yield
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def make_database(url):
    """sqlite:///:memory: | sqlite:///ruta.db | mysql://usuario:clave@host:3306/base"""
    parsed = urlparse(url)
    if parsed.scheme == "sqlite":
        return SQLiteDB(parsed.path[1:] or ":memory:")
    if parsed.scheme == "mysql":
        return MySQLDB(parsed.hostname, parsed.port or 3306, unquote(parsed.username or ""),
                       unquote(parsed.password or ""), parsed.path.lstrip("/"))
    raise ValueError(f"Base de datos no soportada: {parsed.scheme}")
