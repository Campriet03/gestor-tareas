"""Pruebas del adaptador MySQL con un controlador simulado (no necesitan servidor)."""
import sys
import types
import unittest
from datetime import date, datetime

from app.db import MySQLDB, SQLiteDB, make_database, split_sql


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.lastrowid = 42

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        self.conn.log.append(("execute", sql, tuple(params)))

    def fetchall(self):
        return [{"id": 1, "created_at": datetime(2026, 11, 11, 9, 30, 5), "due_date": date(2026, 12, 1), "n": 3}]


class FakeConn:
    def __init__(self, **cfg):
        self.cfg, self.log = cfg, []

    def cursor(self):
        return FakeCursor(self)

    def ping(self, reconnect=False):
        self.log.append(("ping", reconnect))

    def begin(self):
        self.log.append(("begin",))

    def commit(self):
        self.log.append(("commit",))

    def rollback(self):
        self.log.append(("rollback",))


class MySQLAdapterTests(unittest.TestCase):
    def setUp(self):
        fake = types.ModuleType("pymysql")
        fake.cursors = types.SimpleNamespace(DictCursor=object)
        self.created = []

        def connect(**cfg):
            conn = FakeConn(**cfg)
            self.created.append(conn)
            return conn
        fake.connect = connect
        self._saved = {k: sys.modules.get(k) for k in ("pymysql", "pymysql.cursors")}
        sys.modules["pymysql"], sys.modules["pymysql.cursors"] = fake, fake.cursors
        self.db = MySQLDB("127.0.0.1", 3306, "app", "clave", "gestor")

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value

    def test_placeholders_are_converted_and_dates_become_text(self):
        rows = self.db.query("SELECT * FROM tasks WHERE id = ? AND status = ?", (1, "todo"))
        executed = self.created[0].log[-1]
        self.assertEqual(executed, ("execute", "SELECT * FROM tasks WHERE id = %s AND status = %s", (1, "todo")))
        self.assertEqual(rows[0]["created_at"], "2026-11-11 09:30:05")
        self.assertEqual(rows[0]["due_date"], "2026-12-01")
        self.assertEqual(rows[0]["n"], 3)

    def test_execute_returns_lastrowid_and_reuses_connection(self):
        self.assertEqual(self.db.execute("INSERT INTO teams (name, owner_id) VALUES (?, ?)", ("A", 1)), 42)
        self.db.query_one("SELECT 1")
        self.assertEqual(len(self.created), 1)
        self.assertIn(("ping", True), self.created[0].log)

    def test_transaction_commits_and_rolls_back(self):
        with self.db.transaction():
            self.db.execute("UPDATE tasks SET status = ? WHERE id = ?", ("done", 1))
        log = self.created[0].log
        self.assertEqual([e[0] for e in log if e[0] in ("begin", "commit", "rollback")], ["begin", "commit"])
        with self.assertRaises(RuntimeError):
            with self.db.transaction():
                raise RuntimeError("fallo")
        self.assertEqual(log[-1], ("rollback",))

    def test_connection_uses_utf8mb4_and_autocommit(self):
        self.db.query("SELECT 1")
        cfg = self.created[0].cfg
        self.assertEqual((cfg["charset"], cfg["autocommit"], cfg["database"]), ("utf8mb4", True, "gestor"))


class HelperTests(unittest.TestCase):
    def test_make_database_parses_urls(self):
        db = make_database("mysql://app:p%40ss%23word@db.local:3307/gestor")
        self.assertIsInstance(db, MySQLDB)
        self.assertEqual((db._cfg["host"], db._cfg["port"], db._cfg["user"], db._cfg["password"], db._cfg["database"]),
                         ("db.local", 3307, "app", "p@ss#word", "gestor"))
        self.assertIsInstance(make_database("sqlite:///:memory:"), SQLiteDB)
        with self.assertRaises(ValueError):
            make_database("postgres://x")

    def test_split_sql_ignores_comments(self):
        script = "-- comentario; con punto y coma\nCREATE TABLE a (id INT);\n\nCREATE TABLE b (id INT);\n"
        self.assertEqual(split_sql(script), ["CREATE TABLE a (id INT)", "CREATE TABLE b (id INT)"])

    def test_both_schemas_define_the_same_tables(self):
        from app.db import DB_DIR
        import re
        names = {}
        for f in ("schema.mysql.sql", "schema.sqlite.sql"):
            names[f] = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", (DB_DIR / f).read_text()))
        self.assertEqual(names["schema.mysql.sql"], names["schema.sqlite.sql"])
        self.assertEqual(len(names["schema.mysql.sql"]), 7)

    def test_sqlite_transaction_rolls_back(self):
        db = SQLiteDB()
        db.init_schema()
        with self.assertRaises(RuntimeError):
            with db.transaction():
                db.execute("INSERT INTO users (name, email, password_hash) VALUES ('a', 'a@b.co', 'x')")
                raise RuntimeError
        self.assertEqual(db.query("SELECT COUNT(*) AS n FROM users")[0]["n"], 0)


if __name__ == "__main__":
    unittest.main()
