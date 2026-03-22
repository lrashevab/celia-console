# -*- coding: utf-8 -*-
"""
services/content_db.py — 內容工作室 SQLite 服務層
資料表：ideas / drafts / schedule / performance
"""
import json
import sqlite3
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "content.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """建立資料表（若不存在）"""
    with _conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS ideas (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            content     TEXT DEFAULT '',
            category    TEXT DEFAULT '生活',
            source      TEXT DEFAULT '生活觀察',
            tags        TEXT DEFAULT '[]',
            status      TEXT DEFAULT 'new',
            created_at  TEXT,
            updated_at  TEXT
        );

        CREATE TABLE IF NOT EXISTS drafts (
            id               TEXT PRIMARY KEY,
            idea_id          TEXT,
            platform         TEXT NOT NULL DEFAULT 'both',
            title            TEXT DEFAULT '',
            content_threads  TEXT DEFAULT '',
            content_xhs      TEXT DEFAULT '',
            hashtags         TEXT DEFAULT '[]',
            cover_prompt     TEXT DEFAULT '',
            status           TEXT DEFAULT 'draft',
            created_at       TEXT,
            updated_at       TEXT
        );

        CREATE TABLE IF NOT EXISTS schedule (
            id               TEXT PRIMARY KEY,
            draft_id         TEXT NOT NULL,
            platform         TEXT NOT NULL,
            scheduled_at     TEXT,
            published_at     TEXT,
            status           TEXT DEFAULT 'pending',
            post_url         TEXT DEFAULT '',
            threads_post_id  TEXT DEFAULT '',
            created_at       TEXT
        );

        CREATE TABLE IF NOT EXISTS performance (
            id           TEXT PRIMARY KEY,
            schedule_id  TEXT NOT NULL,
            platform     TEXT NOT NULL,
            likes        INTEGER DEFAULT 0,
            comments     INTEGER DEFAULT 0,
            reposts      INTEGER DEFAULT 0,
            reach        INTEGER DEFAULT 0,
            saves        INTEGER DEFAULT 0,
            recorded_at  TEXT
        );
        """)


def _new_id(prefix: str, table: str) -> str:
    with _conn() as conn:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        n = (row[0] or 0) + 1
    return f"{prefix}-{n:03d}"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── Ideas CRUD ────────────────────────────────────────

def add_idea(title: str, content: str = "", category: str = "生活",
             source: str = "生活觀察", tags: list = None) -> str:
    idea_id = _new_id("IDEA", "ideas")
    ts = now_str()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO ideas VALUES (?,?,?,?,?,?,?,?,?)",
            (idea_id, title, content, category, source,
             json.dumps(tags or [], ensure_ascii=False),
             "new", ts, ts)
        )
    return idea_id


def get_ideas(status: str = None) -> list[dict]:
    sql = "SELECT * FROM ideas"
    params = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY created_at DESC"
    with _conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d.get("tags") or "[]")
        result.append(d)
    return result


def update_idea(idea_id: str, **kwargs) -> None:
    kwargs["updated_at"] = now_str()
    if "tags" in kwargs and isinstance(kwargs["tags"], list):
        kwargs["tags"] = json.dumps(kwargs["tags"], ensure_ascii=False)
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [idea_id]
    with _conn() as conn:
        conn.execute(f"UPDATE ideas SET {sets} WHERE id = ?", vals)


def delete_idea(idea_id: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM ideas WHERE id = ?", (idea_id,))


# ── Drafts CRUD ───────────────────────────────────────

def add_draft(idea_id: str = None, platform: str = "both",
              title: str = "", content_threads: str = "",
              content_xhs: str = "", hashtags: list = None,
              cover_prompt: str = "") -> str:
    draft_id = _new_id("DRAFT", "drafts")
    ts = now_str()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO drafts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (draft_id, idea_id, platform, title, content_threads,
             content_xhs, json.dumps(hashtags or [], ensure_ascii=False),
             cover_prompt, "draft", ts, ts)
        )
    return draft_id


def get_drafts(status: str = None, idea_id: str = None) -> list[dict]:
    sql = "SELECT * FROM drafts WHERE 1=1"
    params = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if idea_id:
        sql += " AND idea_id = ?"
        params.append(idea_id)
    sql += " ORDER BY updated_at DESC"
    with _conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["hashtags"] = json.loads(d.get("hashtags") or "[]")
        result.append(d)
    return result


def update_draft(draft_id: str, **kwargs) -> None:
    kwargs["updated_at"] = now_str()
    if "hashtags" in kwargs and isinstance(kwargs["hashtags"], list):
        kwargs["hashtags"] = json.dumps(kwargs["hashtags"], ensure_ascii=False)
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [draft_id]
    with _conn() as conn:
        conn.execute(f"UPDATE drafts SET {sets} WHERE id = ?", vals)


# ── Schedule CRUD ─────────────────────────────────────

def add_schedule(draft_id: str, platform: str, scheduled_at: str) -> str:
    sched_id = _new_id("SCHED", "schedule")
    with _conn() as conn:
        conn.execute(
            "INSERT INTO schedule VALUES (?,?,?,?,?,?,?,?,?)",
            (sched_id, draft_id, platform, scheduled_at,
             None, "pending", "", "", now_str())
        )
    return sched_id


def get_schedule(from_date: str = None, to_date: str = None) -> list[dict]:
    sql = """
        SELECT s.*, d.title, d.content_threads, d.content_xhs, d.status as draft_status
        FROM schedule s
        LEFT JOIN drafts d ON s.draft_id = d.id
        WHERE 1=1
    """
    params = []
    if from_date:
        sql += " AND s.scheduled_at >= ?"
        params.append(from_date)
    if to_date:
        sql += " AND s.scheduled_at <= ?"
        params.append(to_date + " 23:59:59")
    sql += " ORDER BY s.scheduled_at"
    with _conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def update_schedule(sched_id: str, **kwargs) -> None:
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [sched_id]
    with _conn() as conn:
        conn.execute(f"UPDATE schedule SET {sets} WHERE id = ?", vals)


# ── Performance CRUD ──────────────────────────────────

def upsert_performance(schedule_id: str, platform: str, **metrics) -> None:
    with _conn() as conn:
        existing = conn.execute(
            "SELECT id FROM performance WHERE schedule_id = ? AND platform = ?",
            (schedule_id, platform)
        ).fetchone()
        if existing:
            sets = ", ".join(f"{k} = ?" for k in metrics)
            sets += ", recorded_at = ?"
            vals = list(metrics.values()) + [now_str(), existing["id"]]
            conn.execute(f"UPDATE performance SET {sets} WHERE id = ?", vals)
        else:
            perf_id = _new_id("PERF", "performance")
            conn.execute(
                "INSERT INTO performance VALUES (?,?,?,?,?,?,?,?,?)",
                (perf_id, schedule_id, platform,
                 metrics.get("likes", 0), metrics.get("comments", 0),
                 metrics.get("reposts", 0), metrics.get("reach", 0),
                 metrics.get("saves", 0), now_str())
            )


def get_performance_summary() -> list[dict]:
    sql = """
        SELECT p.platform,
               SUM(p.likes) as total_likes,
               SUM(p.comments) as total_comments,
               SUM(p.reposts) as total_reposts,
               SUM(p.reach) as total_reach,
               SUM(p.saves) as total_saves,
               COUNT(*) as post_count
        FROM performance p
        GROUP BY p.platform
    """
    with _conn() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


# 啟動時自動初始化
init_db()
