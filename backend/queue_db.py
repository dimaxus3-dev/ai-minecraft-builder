"""Очередь запросов в SQLite.

Одна таблица и несколько функций — ничего больше на день не нужно.
Статусы: pending -> approved -> generating -> building -> done
         и в сторону: rejected, failed.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_FILE = Path(os.getenv("DB_FILE", "data/queue.db"))

PENDING, APPROVED, GENERATING = "pending", "approved", "generating"
BUILDING, DONE, REJECTED, FAILED = "building", "done", "rejected", "failed"
ACTIVE = (APPROVED, GENERATING, BUILDING)

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    text       TEXT    NOT NULL,
    author     TEXT    NOT NULL DEFAULT '',
    status     TEXT    NOT NULL DEFAULT 'pending',
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL,
    error      TEXT    NOT NULL DEFAULT '',
    program    TEXT    NOT NULL DEFAULT '',
    origin     TEXT    NOT NULL DEFAULT '',
    blocks     INTEGER NOT NULL DEFAULT 0,
    ip         TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_status ON requests(status);
"""

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def hash_ip(ip: str) -> str:
    """IP в базе храним только хешем: для лимита «1 запрос в минуту» его
    достаточно, а восстановить адрес человека из базы уже нельзя."""
    if not ip:
        return ""
    salt = os.getenv("IP_SALT") or os.getenv("ADMIN_SECRET", "dev")
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:16]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    """Одно соединение на процесс. WAL, чтобы чтение не блокировало запись."""
    global _conn
    if _conn is None:
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(SCHEMA)
        _conn.commit()
    return _conn


def _run(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    conn = connect()
    with _lock:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur


def as_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Строка БД -> словарь для JSON. program и origin разворачиваем обратно."""
    if row is None:
        return None
    d = dict(row)
    d.pop("ip", None)          # даже хеш наружу не отдаём
    d["program"] = json.loads(d["program"]) if d["program"] else None
    d["origin"] = json.loads(d["origin"]) if d["origin"] else None
    return d


# --- запись --------------------------------------------------------------

def add(text: str, author: str = "", ip: str = "") -> dict:
    """Новый запрос от человека."""
    stamp = now()
    cur = _run(
        "INSERT INTO requests (text, author, status, created_at, updated_at, ip)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (text.strip()[:300], author.strip()[:40], PENDING, stamp, stamp,
         hash_ip(ip)),
    )
    return get(cur.lastrowid)          # type: ignore[arg-type]


def set_status(request_id: int, status: str, error: str = "") -> dict | None:
    _run("UPDATE requests SET status=?, error=?, updated_at=? WHERE id=?",
         (status, error[:500], now(), request_id))
    return get(request_id)


def set_program(request_id: int, program: dict) -> dict | None:
    """Программа от LLM. Где строить — решает воркер, он знает мир."""
    _run("UPDATE requests SET program=?, updated_at=? WHERE id=?",
         (json.dumps(program, ensure_ascii=False), now(), request_id))
    return get(request_id)


def clear_program(request_id: int) -> dict | None:
    """Чертёж больше не подходит к тексту (его поправили) — забываем его."""
    _run("UPDATE requests SET program='', updated_at=? WHERE id=?",
         (now(), request_id))
    return get(request_id)


def set_result(request_id: int, origin: list[int], blocks: int) -> dict | None:
    """Итог стройки: куда поставили и сколько блоков."""
    _run("UPDATE requests SET origin=?, blocks=?, updated_at=? WHERE id=?",
         (json.dumps(origin), blocks, now(), request_id))
    return get(request_id)


def update_text(request_id: int, text: str) -> dict | None:
    """Правка текста в админке перед одобрением."""
    _run("UPDATE requests SET text=?, updated_at=? WHERE id=?",
         (text.strip()[:300], now(), request_id))
    return get(request_id)


# --- чтение --------------------------------------------------------------

def get(request_id: int) -> dict | None:
    cur = _run("SELECT * FROM requests WHERE id=?", (request_id,))
    return as_dict(cur.fetchone())


def recent(limit: int = 50) -> list[dict]:
    cur = _run("SELECT * FROM requests ORDER BY id DESC LIMIT ?", (limit,))
    return [as_dict(r) for r in cur.fetchall()]        # type: ignore[misc]


def next_approved() -> dict | None:
    """Самый старый одобренный запрос — его воркер и будет строить."""
    cur = _run("SELECT * FROM requests WHERE status=? ORDER BY id LIMIT 1",
               (APPROVED,))
    return as_dict(cur.fetchone())


def stuck_active() -> list[dict]:
    """Запросы, зависшие в работе (например, воркер умер посреди стройки)."""
    cur = _run(
        f"SELECT * FROM requests WHERE status IN ({','.join('?' * len(ACTIVE))})"
        " ORDER BY id", ACTIVE)
    return [as_dict(r) for r in cur.fetchall()]        # type: ignore[misc]


def stats() -> dict:
    """Счётчики для экрана в зале."""
    cur = _run("SELECT status, COUNT(*) c FROM requests GROUP BY status")
    by_status = {r["status"]: r["c"] for r in cur.fetchall()}
    cur = _run("SELECT COALESCE(SUM(blocks), 0) s FROM requests WHERE status=?",
               (DONE,))
    return {
        "by_status": by_status,
        "built": by_status.get(DONE, 0),
        "waiting": by_status.get(PENDING, 0) + by_status.get(APPROVED, 0),
        "blocks": cur.fetchone()["s"],
        "total": sum(by_status.values()),
    }


def last_from_ip(ip: str) -> dict | None:
    """Для лимита «один запрос в минуту с одного адреса»."""
    cur = _run("SELECT * FROM requests WHERE ip=? ORDER BY id DESC LIMIT 1",
               (hash_ip(ip),))
    return as_dict(cur.fetchone())
