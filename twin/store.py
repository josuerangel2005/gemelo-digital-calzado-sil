"""Persistencia del estado del gemelo digital (SQLite)."""
import os
import sqlite3

DB_PATH = os.getenv("TWIN_DB", "twin.db")


class TwinStore:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS decisiones (
                    pieza_id INTEGER, timestamp REAL, decision TEXT,
                    label TEXT, score REAL, latencia_ms REAL)"""
            )

    def _conn(self):
        return sqlite3.connect(self.path)

    def save(self, d: dict):
        with self._conn() as c:
            c.execute(
                "INSERT INTO decisiones VALUES (?,?,?,?,?,?)",
                (d["pieza_id"], d["timestamp"], d["decision"], d["label"], d["score"], d["latencia_ms"]),
            )

    def all(self) -> list[dict]:
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            return [dict(r) for r in c.execute("SELECT * FROM decisiones ORDER BY timestamp")]
