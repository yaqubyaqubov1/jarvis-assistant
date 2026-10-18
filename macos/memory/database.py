import json
import sqlite3
from datetime import datetime
from config import DB_PATH, DATA_DIR

def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    return db

def init_database():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS memories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key);

        CREATE TABLE IF NOT EXISTS reminders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            due_at TEXT NOT NULL,
            recurrence TEXT,
            kind TEXT NOT NULL DEFAULT 'reminder',
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS task_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request TEXT NOT NULL,
            plan TEXT,
            result TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS preferences(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS aliases(
            alias TEXT PRIMARY KEY,
            target TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS modes(
            name TEXT PRIMARY KEY,
            config_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)

def remember(key, value):
    with connect() as db:
        db.execute("INSERT INTO memories(key,value,created_at) VALUES(?,?,?)",
                   (str(key).strip().lower(), str(value).strip(), datetime.now().isoformat()))

def recall(key):
    with connect() as db:
        row = db.execute("SELECT value FROM memories WHERE key=? ORDER BY id DESC LIMIT 1",
                         (str(key).strip().lower(),)).fetchone()
    return row["value"] if row else None

def add_reminder(message, due_at, recurrence=None, kind="reminder"):
    with connect() as db:
        cur = db.execute("""INSERT INTO reminders(message,due_at,recurrence,kind,created_at)
                            VALUES(?,?,?,?,?)""",
                         (message, due_at, recurrence, kind, datetime.now().isoformat()))
        return cur.lastrowid

def list_reminders(kind=None):
    with connect() as db:
        if kind:
            rows = db.execute("""SELECT id,message,due_at,recurrence,kind FROM reminders
                                 WHERE enabled=1 AND kind=? ORDER BY due_at""", (kind,)).fetchall()
        else:
            rows = db.execute("""SELECT id,message,due_at,recurrence,kind FROM reminders
                                 WHERE enabled=1 ORDER BY due_at""").fetchall()
    return [tuple(r) for r in rows]

def due_reminders(now_iso):
    with connect() as db:
        rows = db.execute("""SELECT id,message,due_at,recurrence,kind FROM reminders
                             WHERE enabled=1 AND due_at<=? ORDER BY due_at""", (now_iso,)).fetchall()
    return [tuple(r) for r in rows]

def update_reminder_due(reminder_id, due_at):
    with connect() as db:
        db.execute("UPDATE reminders SET due_at=? WHERE id=?", (due_at, reminder_id))

def disable_reminder(reminder_id):
    with connect() as db:
        db.execute("UPDATE reminders SET enabled=0 WHERE id=?", (reminder_id,))

def cancel_reminder(reminder_id):
    disable_reminder(reminder_id)

def save_task(request, plan, result):
    with connect() as db:
        db.execute("INSERT INTO task_history(request,plan,result,created_at) VALUES(?,?,?,?)",
                   (request, plan, result, datetime.now().isoformat()))

def recent_tasks(limit=10):
    with connect() as db:
        rows = db.execute("""SELECT request,result,created_at FROM task_history
                             ORDER BY id DESC LIMIT ?""", (int(limit),)).fetchall()
    return [tuple(r) for r in rows]

def set_preference(key, value):
    with connect() as db:
        db.execute("""INSERT INTO preferences(key,value,updated_at) VALUES(?,?,?)
                      ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
                   (str(key).lower().strip(), str(value), datetime.now().isoformat()))

def get_preference(key):
    with connect() as db:
        row = db.execute("SELECT value FROM preferences WHERE key=?", (str(key).lower().strip(),)).fetchone()
    return row["value"] if row else None

def all_preferences():
    with connect() as db:
        return [(r["key"], r["value"]) for r in db.execute("SELECT key,value FROM preferences ORDER BY key")]

def set_alias(alias, target):
    with connect() as db:
        db.execute("""INSERT INTO aliases(alias,target,updated_at) VALUES(?,?,?)
                      ON CONFLICT(alias) DO UPDATE SET target=excluded.target,updated_at=excluded.updated_at""",
                   (str(alias).lower().strip(), str(target).strip(), datetime.now().isoformat()))

def resolve_alias(alias):
    with connect() as db:
        row = db.execute("SELECT target FROM aliases WHERE alias=?", (str(alias).lower().strip(),)).fetchone()
    return row["target"] if row else None

def all_aliases():
    with connect() as db:
        return [(r["alias"], r["target"]) for r in db.execute("SELECT alias,target FROM aliases ORDER BY alias")]

def set_mode(name, config):
    with connect() as db:
        db.execute("""INSERT INTO modes(name,config_json,updated_at) VALUES(?,?,?)
                      ON CONFLICT(name) DO UPDATE SET config_json=excluded.config_json,updated_at=excluded.updated_at""",
                   (str(name).lower().strip(), json.dumps(config), datetime.now().isoformat()))

def get_mode(name):
    with connect() as db:
        row = db.execute("SELECT config_json FROM modes WHERE name=?", (str(name).lower().strip(),)).fetchone()
    return json.loads(row["config_json"]) if row else None
