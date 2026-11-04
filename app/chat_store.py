"""AI 채팅방 저장소: app/chats.sqlite (장부 파일과 별도, gitignore).

- 방(chat)은 로그인 이메일(owner)이 소유한다. 다른 사용자의 방은 없는 것으로 본다 (ChatNotFound).
- 메시지(message)는 role user/assistant, 내용, 조회(calls)·제안(proposals) JSON, note(제안 처리 알림) 플래그.
- 마지막 메시지(updated)가 KEEP_DAYS 를 넘은 방은 보관(kept)이 아니면 purge() 가 지운다 (서버 시작·목록 조회 때).
- 모델에는 history() 로 최근 HISTORY_LIMIT 개만 보낸다. 장부 백업·되돌리기·내보내기와 무관하다.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
CHAT_DB = Path(os.environ.get("LEDGER_CHAT_DB") or APP_DIR / "chats.sqlite")
KEEP_DAYS = 7
HISTORY_LIMIT = 40
TITLE_LEN = 30
TITLE_MAX = 60

_DDL = (
    "CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, title TEXT NOT NULL DEFAULT '', "
    "kept INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL, updated TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS chat_owner ON chat (owner, updated)",
    "CREATE TABLE IF NOT EXISTS message (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL REFERENCES chat(id) ON DELETE CASCADE, "
    "seq INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, calls TEXT, proposals TEXT, note INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS message_chat ON message (chat_id, seq)",
)


class ChatNotFound(LookupError):
    pass


def _now() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat(sep=" ")


def _connect() -> sqlite3.Connection:
    CHAT_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(CHAT_DB))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    for ddl in _DDL:
        con.execute(ddl)
    return con


def _chat_out(r: sqlite3.Row, count: int | None = None) -> dict:
    d = {"id": r["id"], "title": r["title"], "kept": bool(r["kept"]), "created": r["created"], "updated": r["updated"]}
    if count is not None:
        d["count"] = count
    return d


def _msg_out(r: sqlite3.Row) -> dict:
    return {"id": r["id"], "seq": r["seq"], "role": r["role"], "content": r["content"], "note": bool(r["note"]), "created": r["created"],
            "calls": json.loads(r["calls"]) if r["calls"] else [], "proposals": json.loads(r["proposals"]) if r["proposals"] else []}


def purge(now: dt.datetime | None = None) -> int:
    """보관하지 않은 방 중 마지막 메시지가 KEEP_DAYS 를 넘은 방을 지운다. 지운 방 수 반환."""
    limit = ((now or dt.datetime.now()) - dt.timedelta(days=KEEP_DAYS)).replace(microsecond=0).isoformat(sep=" ")
    with _connect() as con:
        cur = con.execute("DELETE FROM chat WHERE kept = 0 AND updated < ?", (limit,))
        return cur.rowcount


def list_chats(owner: str) -> list[dict]:
    """사용자의 방 목록, 최근 활동순. 먼저 오래된 방을 정리한다."""
    purge()
    with _connect() as con:
        rows = con.execute("SELECT c.*, (SELECT COUNT(*) FROM message m WHERE m.chat_id = c.id AND m.note = 0) AS n "
                           "FROM chat c WHERE owner = ? ORDER BY updated DESC, id DESC", (owner,)).fetchall()
    return [_chat_out(r, r["n"]) for r in rows]


def create_chat(owner: str, title: str = "") -> dict:
    now = _now()
    with _connect() as con:
        cur = con.execute("INSERT INTO chat (owner, title, kept, created, updated) VALUES (?, ?, 0, ?, ?)", (owner, _clean_title(title), now, now))
        return _chat_out(con.execute("SELECT * FROM chat WHERE id = ?", (cur.lastrowid,)).fetchone(), 0)


def _row(con: sqlite3.Connection, owner: str, chat_id: int) -> sqlite3.Row:
    r = con.execute("SELECT * FROM chat WHERE id = ? AND owner = ?", (chat_id, owner)).fetchone()
    if r is None:
        raise ChatNotFound("채팅방을 찾을 수 없습니다.")
    return r


def get_chat(owner: str, chat_id: int) -> dict:
    with _connect() as con:
        r = _row(con, owner, chat_id)
        n = con.execute("SELECT COUNT(*) FROM message WHERE chat_id = ? AND note = 0", (chat_id,)).fetchone()[0]
        return _chat_out(r, n)


def _clean_title(title: str) -> str:
    return " ".join(str(title or "").split())[:TITLE_MAX]


def update_chat(owner: str, chat_id: int, title: str | None = None, kept: bool | None = None) -> dict:
    with _connect() as con:
        _row(con, owner, chat_id)
        if title is not None:
            t = _clean_title(title)
            if not t:
                raise ValueError("제목을 입력하세요.")
            con.execute("UPDATE chat SET title = ? WHERE id = ?", (t, chat_id))
        if kept is not None:
            con.execute("UPDATE chat SET kept = ? WHERE id = ?", (1 if kept else 0, chat_id))
    return get_chat(owner, chat_id)


def delete_chat(owner: str, chat_id: int):
    with _connect() as con:
        _row(con, owner, chat_id)
        con.execute("DELETE FROM chat WHERE id = ?", (chat_id,))


def messages(owner: str, chat_id: int) -> list[dict]:
    with _connect() as con:
        _row(con, owner, chat_id)
        rows = con.execute("SELECT * FROM message WHERE chat_id = ? ORDER BY seq", (chat_id,)).fetchall()
    return [_msg_out(r) for r in rows]


def add_message(owner: str, chat_id: int, role: str, content: str, calls: list | None = None, proposals: list | None = None,
                note: bool = False) -> dict:
    """메시지 추가. 방의 updated 를 갱신하고, 제목이 비어 있으면 첫 사용자 질문의 앞 TITLE_LEN 자를 제목으로 쓴다."""
    if role not in ("user", "assistant"):
        raise ValueError("role 은 user 또는 assistant 여야 합니다.")
    now = _now()
    with _connect() as con:
        r = _row(con, owner, chat_id)
        seq = (con.execute("SELECT COALESCE(MAX(seq), 0) FROM message WHERE chat_id = ?", (chat_id,)).fetchone()[0] or 0) + 1
        cur = con.execute("INSERT INTO message (chat_id, seq, role, content, calls, proposals, note, created) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          (chat_id, seq, role, str(content or ""), json.dumps(calls or [], ensure_ascii=False, default=str) if calls else None,
                           json.dumps(proposals or [], ensure_ascii=False, default=str) if proposals else None, 1 if note else 0, now))
        title = r["title"]
        if not title and role == "user" and not note:
            title = _clean_title(content)[:TITLE_LEN]
        con.execute("UPDATE chat SET updated = ?, title = ? WHERE id = ?", (now, title, chat_id))
        return _msg_out(con.execute("SELECT * FROM message WHERE id = ?", (cur.lastrowid,)).fetchone())


def history(owner: str, chat_id: int, limit: int = HISTORY_LIMIT) -> list[dict]:
    """모델에 보낼 최근 메시지 (role, content). 알림(note)도 사용자 메시지로 들어간다."""
    with _connect() as con:
        _row(con, owner, chat_id)
        rows = con.execute("SELECT role, content FROM message WHERE chat_id = ? ORDER BY seq DESC LIMIT ?", (chat_id, max(1, limit))).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
