"""SQLite database initialisation and helper utilities."""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "dnd_helper.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS characters (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id     INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
            name            TEXT NOT NULL,
            player_name     TEXT DEFAULT '',
            race            TEXT DEFAULT '',
            class           TEXT DEFAULT '',
            subclass        TEXT DEFAULT '',
            level           INTEGER DEFAULT 1,
            background      TEXT DEFAULT '',
            alignment       TEXT DEFAULT '',
            xp              INTEGER DEFAULT 0,
            ability_scores  TEXT DEFAULT '{}',
            save_profs      TEXT DEFAULT '[]',
            skill_profs     TEXT DEFAULT '[]',
            hp_max          INTEGER DEFAULT 0,
            hp_current      INTEGER DEFAULT 0,
            hp_temp         INTEGER DEFAULT 0,
            ac              INTEGER DEFAULT 10,
            speed           INTEGER DEFAULT 30,
            initiative_bonus INTEGER DEFAULT 0,
            features        TEXT DEFAULT '[]',
            equipment       TEXT DEFAULT '[]',
            currency        TEXT DEFAULT '{"pp":0,"gp":0,"ep":0,"sp":0,"cp":0}',
            spells          TEXT DEFAULT '{}',
            spell_slots     TEXT DEFAULT '{}',
            notes           TEXT DEFAULT '',
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS quests (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            title       TEXT NOT NULL,
            description TEXT DEFAULT '',
            status      TEXT DEFAULT 'active',
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS locations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            notes       TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS npcs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id     INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            name            TEXT NOT NULL,
            description     TEXT DEFAULT '',
            relationship    TEXT DEFAULT '',
            notes           TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id     INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            title           TEXT NOT NULL,
            description     TEXT DEFAULT '',
            date_in_game    TEXT DEFAULT '',
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS campaign_images (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            name        TEXT NOT NULL,
            data        BLOB NOT NULL,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS creatures (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL UNIQUE,
            size            TEXT DEFAULT '',
            alignment       TEXT DEFAULT '',
            challenge       TEXT DEFAULT '',
            hit_points      TEXT DEFAULT '',
            armor_class     TEXT DEFAULT '',
            speed           TEXT DEFAULT '',
            str_score       INTEGER DEFAULT 10,
            dex_score       INTEGER DEFAULT 10,
            con_score       INTEGER DEFAULT 10,
            int_score       INTEGER DEFAULT 10,
            wis_score       INTEGER DEFAULT 10,
            cha_score       INTEGER DEFAULT 10,
            str_mod         TEXT DEFAULT '(+0)',
            dex_mod         TEXT DEFAULT '(+0)',
            con_mod         TEXT DEFAULT '(+0)',
            int_mod         TEXT DEFAULT '(+0)',
            wis_mod         TEXT DEFAULT '(+0)',
            cha_mod         TEXT DEFAULT '(+0)',
            skills          TEXT DEFAULT '',
            saving_throws   TEXT DEFAULT '',
            senses          TEXT DEFAULT '',
            languages       TEXT DEFAULT '',
            abilities       TEXT DEFAULT '',
            tags            TEXT DEFAULT '[]',
            source          TEXT DEFAULT 'bestiary'
        );

        CREATE TABLE IF NOT EXISTS spells (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL UNIQUE,
            level           INTEGER DEFAULT 0,
            school          TEXT DEFAULT '',
            casting_time    TEXT DEFAULT '',
            range           TEXT DEFAULT '',
            components      TEXT DEFAULT '',
            duration        TEXT DEFAULT '',
            description     TEXT DEFAULT '',
            classes         TEXT DEFAULT '',
            source          TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            type        TEXT DEFAULT '',
            rarity      TEXT DEFAULT 'common',
            description TEXT DEFAULT '',
            properties  TEXT DEFAULT '{}',
            source      TEXT DEFAULT ''
        );
        """)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def jloads(val):
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return val
    return val


def jdumps(val) -> str:
    return json.dumps(val, ensure_ascii=False)
