"""
database.py – Complete SQLite persistence layer for WaifuBot
Includes: Auto-Migrations & Auto-JSON Database Sync
"""

import sqlite3
import os
import json
from datetime import datetime

# Path configuration
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "waifubot.db")
JSON_PATH = os.path.join(DATA_DIR, "database_backup.json")

def _conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con

def sync_to_json():
    """Automatically exports the SQLite database to a JSON file."""
    try:
        data = {
            "exported_at": datetime.now().isoformat(),
            "characters": [],
            "users": [],
            "stats": {}
        }
        with _conn() as con:
            data["characters"] = [dict(row) for row in con.execute("SELECT * FROM characters").fetchall()]
            data["users"] = [dict(row) for row in con.execute("SELECT * FROM users").fetchall()]
        
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"JSON Sync Error: {e}")

def init_db():
    """Initializes tables and automatically repairs missing columns (Migrations)."""
    with _conn() as con:
        # 1. CREATE TABLES (Standard Schema)
        con.executescript("""
        CREATE TABLE IF NOT EXISTS characters (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            anime       TEXT    NOT NULL,
            rarity      TEXT    NOT NULL DEFAULT '⭐ Common',
            image_url   TEXT,
            added_by    INTEGER,
            is_custom   INTEGER DEFAULT 0,
            owner_id    INTEGER DEFAULT NULL,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id         INTEGER PRIMARY KEY,
            username        TEXT,
            first_name      TEXT,
            coins           INTEGER DEFAULT 0,
            catches         INTEGER DEFAULT 0,
            last_daily      TEXT,
            last_duel       TEXT,
            wins            INTEGER DEFAULT 0,
            losses          INTEGER DEFAULT 0,
            banned          INTEGER DEFAULT 0,
            milestone_level INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS collections (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            char_id     INTEGER NOT NULL,
            caught_at   TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (char_id) REFERENCES characters(id)
        );

        CREATE TABLE IF NOT EXISTS active_spawns (
            group_id    INTEGER PRIMARY KEY,
            char_id     INTEGER NOT NULL,
            message_id  INTEGER,
            spawned_at  TEXT    DEFAULT (datetime('now')),
            caught_by   INTEGER DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS trades (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user       INTEGER NOT NULL,
            to_user         INTEGER NOT NULL,
            from_char_id    INTEGER NOT NULL,
            to_char_id      INTEGER,
            coins_offered   INTEGER DEFAULT 0,
            status          TEXT    DEFAULT 'pending',
            created_at      TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS redeem_codes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT    NOT NULL UNIQUE,
            coins       INTEGER DEFAULT 0,
            char_id     INTEGER DEFAULT NULL,
            max_uses    INTEGER DEFAULT 1,
            used_count  INTEGER DEFAULT 0,
            created_by  INTEGER,
            expires_at  TEXT    DEFAULT NULL,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS redeem_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT    NOT NULL,
            user_id     INTEGER NOT NULL,
            redeemed_at TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS leaderboard_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            week        TEXT    NOT NULL,
            rank        INTEGER NOT NULL,
            catches     INTEGER NOT NULL,
            UNIQUE(user_id, week)
        );

        CREATE TABLE IF NOT EXISTS custom_waifu_awards (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            char_id     INTEGER NOT NULL,
            reason      TEXT,
            awarded_at  TEXT    DEFAULT (datetime('now'))
        );
        """)

        # 2. AUTO-MIGRATION (Repairing the DB if it's old)
        cursor = con.cursor()
        
        # Check 'characters' table
        cursor.execute("PRAGMA table_info(characters)")
        char_cols = [c[1] for c in cursor.fetchall()]
        if 'is_custom' not in char_cols:
            con.execute("ALTER TABLE characters ADD COLUMN is_custom INTEGER DEFAULT 0")
        if 'owner_id' not in char_cols:
            con.execute("ALTER TABLE characters ADD COLUMN owner_id INTEGER DEFAULT NULL")

        # Check 'users' table (Fixes "IndexError: wins")
        cursor.execute("PRAGMA table_info(users)")
        user_cols = [c[1] for c in cursor.fetchall()]
        if 'wins' not in user_cols:
            con.execute("ALTER TABLE users ADD COLUMN wins INTEGER DEFAULT 0")
        if 'losses' not in user_cols:
            con.execute("ALTER TABLE users ADD COLUMN losses INTEGER DEFAULT 0")
        if 'milestone_level' not in user_cols:
            con.execute("ALTER TABLE users ADD COLUMN milestone_level INTEGER DEFAULT 0")

    sync_to_json()
    print("✅ Database initialized and sync complete.")

# ── Characters ─────────────────────────────────────────────────────────────
def add_character(name, anime, rarity, image_url, added_by, is_custom=0, owner_id=None):
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO characters (name,anime,rarity,image_url,added_by,is_custom,owner_id) VALUES (?,?,?,?,?,?,?)",
            (name, anime, rarity, image_url, added_by, is_custom, owner_id)
        )
        res = cur.lastrowid
    sync_to_json()
    return res

def get_character(char_id):
    with _conn() as con:
        return con.execute("SELECT * FROM characters WHERE id=?", (char_id,)).fetchone()

def get_all_characters():
    with _conn() as con:
        return con.execute("SELECT * FROM characters WHERE is_custom=0 ORDER BY rarity,name").fetchall()

def update_character(char_id, **fields):
    allowed = {"name","anime","rarity","image_url"}
    updates = {k:v for k,v in fields.items() if k in allowed}
    if not updates: return
    clause = ", ".join(f"{k}=?" for k in updates)
    with _conn() as con:
        con.execute(f"UPDATE characters SET {clause} WHERE id=?", (*updates.values(), char_id))
    sync_to_json()

def delete_character(char_id):
    with _conn() as con:
        con.execute("DELETE FROM collections WHERE char_id=?", (char_id,))
        con.execute("DELETE FROM characters WHERE id=?", (char_id,))
    sync_to_json()

def search_characters(query):
    q = f"%{query}%"
    with _conn() as con:
        return con.execute("SELECT * FROM characters WHERE (name LIKE ? OR anime LIKE ?) AND is_custom=0",(q,q)).fetchall()

# ── Users ──────────────────────────────────────────────────────────────────
def ensure_user(user_id, username="", first_name=""):
    with _conn() as con:
        con.execute("""
            INSERT INTO users (user_id,username,first_name) VALUES (?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name
        """, (user_id, username or "", first_name or ""))
    sync_to_json()

def get_user(user_id):
    with _conn() as con:
        return con.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

def update_coins(user_id, delta):
    with _conn() as con:
        con.execute("UPDATE users SET coins=MAX(0,coins+?) WHERE user_id=?", (delta, user_id))
    sync_to_json()

def increment_catches(user_id):
    with _conn() as con:
        con.execute("UPDATE users SET catches=catches+1 WHERE user_id=?", (user_id,))
    sync_to_json()

def set_last_daily(user_id, dt):
    with _conn() as con:
        con.execute("UPDATE users SET last_daily=? WHERE user_id=?", (dt, user_id))
    sync_to_json()

def set_milestone_level(user_id, level):
    with _conn() as con:
        con.execute("UPDATE users SET milestone_level=? WHERE user_id=?", (level, user_id))
    sync_to_json()

def add_win(user_id):
    with _conn() as con:
        con.execute("UPDATE users SET wins=wins+1 WHERE user_id=?", (user_id,))
    sync_to_json()

def add_loss(user_id):
    with _conn() as con:
        con.execute("UPDATE users SET losses=losses+1 WHERE user_id=?", (user_id,))
    sync_to_json()

def ban_user(user_id):
    with _conn() as con:
        con.execute("UPDATE users SET banned=1 WHERE user_id=?", (user_id,))

def unban_user(user_id):
    with _conn() as con:
        con.execute("UPDATE users SET banned=0 WHERE user_id=?", (user_id,))

def get_leaderboard():
    with _conn() as con:
        return con.execute(
            "SELECT user_id,first_name,username,catches,coins,wins FROM users ORDER BY catches DESC LIMIT 10"
        ).fetchall()

def get_all_user_ids():
    with _conn() as con:
        return [r[0] for r in con.execute("SELECT user_id FROM users WHERE banned=0").fetchall()]

# ── Collections ─────────────────────────────────────────────────────────────
def add_to_collection(user_id, char_id):
    with _conn() as con:
        con.execute("INSERT INTO collections (user_id,char_id) VALUES (?,?)", (user_id, char_id))
    sync_to_json()

def get_collection(user_id, page=0, per_page=10):
    offset = page * per_page
    with _conn() as con:
        return con.execute("""
            SELECT c.id as col_id,c.char_id,ch.name,ch.anime,ch.rarity,ch.image_url,ch.is_custom
            FROM collections c JOIN characters ch ON ch.id=c.char_id
            WHERE c.user_id=? ORDER BY ch.is_custom DESC,ch.rarity,ch.name LIMIT ? OFFSET ?
        """, (user_id, per_page, offset)).fetchall()

def get_full_collection(user_id):
    with _conn() as con:
        return con.execute("""
            SELECT c.id as col_id,c.char_id,ch.name,ch.anime,ch.rarity,ch.image_url,ch.is_custom
            FROM collections c JOIN characters ch ON ch.id=c.char_id
            WHERE c.user_id=? ORDER BY ch.is_custom DESC,ch.rarity,ch.name
        """, (user_id,)).fetchall()

def count_collection(user_id):
    with _conn() as con:
        return con.execute("SELECT COUNT(*) FROM collections WHERE user_id=?", (user_id,)).fetchone()[0]

def has_character(user_id, char_id):
    with _conn() as con:
        return con.execute("SELECT 1 FROM collections WHERE user_id=? AND char_id=?", (user_id, char_id)).fetchone() is not None

def remove_from_collection(user_id, char_id):
    with _conn() as con:
        row = con.execute("SELECT id FROM collections WHERE user_id=? AND char_id=? LIMIT 1", (user_id, char_id)).fetchone()
        if not row: return False
        con.execute("DELETE FROM collections WHERE id=?", (row["id"],))
        return True

# ── Active Spawns ──────────────────────────────────────────────────────────
def set_spawn(group_id, char_id, message_id):
    with _conn() as con:
        con.execute("""
            INSERT INTO active_spawns (group_id,char_id,message_id)
            VALUES (?,?,?)
            ON CONFLICT(group_id) DO UPDATE SET char_id=excluded.char_id,
            message_id=excluded.message_id, spawned_at=datetime('now'), caught_by=NULL
        """, (group_id, char_id, message_id))

def get_spawn(group_id):
    with _conn() as con:
        return con.execute("SELECT * FROM active_spawns WHERE group_id=? AND caught_by IS NULL", (group_id,)).fetchone()

def mark_caught(group_id, user_id):
    with _conn() as con:
        con.execute("UPDATE active_spawns SET caught_by=? WHERE group_id=?", (user_id, group_id))

def clear_spawn(group_id):
    with _conn() as con:
        con.execute("DELETE FROM active_spawns WHERE group_id=?", (group_id,))

# ── Trades ────────────────────────────────────────────────────────────────
def create_trade(from_user, to_user, from_char_id, to_char_id, coins):
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO trades (from_user,to_user,from_char_id,to_char_id,coins_offered) VALUES (?,?,?,?,?)",
            (from_user, to_user, from_char_id, to_char_id, coins)
        )
    sync_to_json()
    return cur.lastrowid

def get_trade(trade_id):
    with _conn() as con:
        return con.execute("SELECT * FROM trades WHERE id=?", (trade_id,)).fetchone()

def update_trade_status(trade_id, status):
    with _conn() as con:
        con.execute("UPDATE trades SET status=? WHERE id=?", (status, trade_id))
    sync_to_json()

# ── Stats ─────────────────────────────────────────────────────────────────
def get_stats():
    with _conn() as con:
        return {
            "total_users":      con.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "total_characters": con.execute("SELECT COUNT(*) FROM characters WHERE is_custom=0").fetchone()[0],
            "custom_waifus":    con.execute("SELECT COUNT(*) FROM characters WHERE is_custom=1").fetchone()[0],
            "total_catches":    con.execute("SELECT SUM(catches) FROM users").fetchone()[0] or 0,
            "total_trades":     con.execute("SELECT COUNT(*) FROM trades WHERE status='accepted'").fetchone()[0],
        }

# Initial Startup
init_db()