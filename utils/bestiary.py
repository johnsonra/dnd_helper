"""Parse creature Markdown files from the bestiary/ Git submodule and
bulk-import them into the local SQLite database."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import frontmatter  # python-frontmatter

from db import get_conn, jdumps

BESTIARY_DIR = Path(__file__).parent.parent / "bestiary" / "_creatures"


def _stat_value(raw: Any) -> int:
    """Extract the integer part from a stat like '21 (+5)' or just '21'."""
    if isinstance(raw, int):
        return raw
    m = re.match(r"(\d+)", str(raw))
    return int(m.group(1)) if m else 10


def _mod_str(raw: Any) -> str:
    """Return the modifier string, e.g. '(+5)' or '(-1)'."""
    if isinstance(raw, (int, float)):
        return f"({raw:+d})"
    s = str(raw)
    m = re.search(r"(\([+-]?\d+\))", s)
    return m.group(1) if m else "(+0)"


def parse_creature_file(path: Path) -> dict | None:
    """Parse a single bestiary creature Markdown file and return a dict."""
    try:
        post = frontmatter.load(str(path))
    except Exception:
        return None

    fm = post.metadata
    if not fm.get("name"):
        return None

    tags = fm.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    return {
        "name":           str(fm.get("name", path.stem)).strip(),
        "size":           str(fm.get("size", "")).strip(),
        "alignment":      str(fm.get("alignment", "")).strip(),
        "challenge":      str(fm.get("challenge", "")).strip(),
        "hit_points":     str(fm.get("hit_points", "")).strip(),
        "armor_class":    str(fm.get("armor_class", "")).strip(),
        "speed":          str(fm.get("speed", "")).strip(),
        "str_score":      _stat_value(fm.get("str", 10)),
        "dex_score":      _stat_value(fm.get("dex", 10)),
        "con_score":      _stat_value(fm.get("con", 10)),
        "int_score":      _stat_value(fm.get("int", 10)),
        "wis_score":      _stat_value(fm.get("wis", 10)),
        "cha_score":      _stat_value(fm.get("cha", 10)),
        "str_mod":        _mod_str(fm.get("str", "(+0)")),
        "dex_mod":        _mod_str(fm.get("dex", "(+0)")),
        "con_mod":        _mod_str(fm.get("con", "(+0)")),
        "int_mod":        _mod_str(fm.get("int", "(+0)")),
        "wis_mod":        _mod_str(fm.get("wis", "(+0)")),
        "cha_mod":        _mod_str(fm.get("cha", "(+0)")),
        "skills":         str(fm.get("skills", "")).strip(),
        "saving_throws":  str(fm.get("saving_throws", "")).strip(),
        "senses":         str(fm.get("senses", "")).strip(),
        "languages":      str(fm.get("languages", "")).strip(),
        "abilities":      post.content.strip(),
        "tags":           jdumps(tags),
        "source":         "bestiary",
    }


def import_all_creatures(progress_callback=None) -> tuple[int, int]:
    """Import all bestiary creatures into the database.

    Returns (imported, skipped) counts.
    """
    if not BESTIARY_DIR.exists():
        return 0, 0

    files = list(BESTIARY_DIR.glob("*.md"))
    imported = 0
    skipped = 0

    with get_conn() as conn:
        for i, f in enumerate(files):
            if progress_callback:
                progress_callback(i / len(files), f.stem)

            data = parse_creature_file(f)
            if data is None:
                skipped += 1
                continue

            try:
                conn.execute(
                    """
                    INSERT INTO creatures
                        (name, size, alignment, challenge, hit_points, armor_class, speed,
                         str_score, dex_score, con_score, int_score, wis_score, cha_score,
                         str_mod, dex_mod, con_mod, int_mod, wis_mod, cha_mod,
                         skills, saving_throws, senses, languages, abilities, tags, source)
                    VALUES
                        (:name, :size, :alignment, :challenge, :hit_points, :armor_class, :speed,
                         :str_score, :dex_score, :con_score, :int_score, :wis_score, :cha_score,
                         :str_mod, :dex_mod, :con_mod, :int_mod, :wis_mod, :cha_mod,
                         :skills, :saving_throws, :senses, :languages, :abilities, :tags, :source)
                    ON CONFLICT(name) DO UPDATE SET
                        size=excluded.size, alignment=excluded.alignment,
                        challenge=excluded.challenge, hit_points=excluded.hit_points,
                        armor_class=excluded.armor_class, speed=excluded.speed,
                        str_score=excluded.str_score, dex_score=excluded.dex_score,
                        con_score=excluded.con_score, int_score=excluded.int_score,
                        wis_score=excluded.wis_score, cha_score=excluded.cha_score,
                        str_mod=excluded.str_mod, dex_mod=excluded.dex_mod,
                        con_mod=excluded.con_mod, int_mod=excluded.int_mod,
                        wis_mod=excluded.wis_mod, cha_mod=excluded.cha_mod,
                        skills=excluded.skills, saving_throws=excluded.saving_throws,
                        senses=excluded.senses, languages=excluded.languages,
                        abilities=excluded.abilities, tags=excluded.tags
                    """,
                    data,
                )
                imported += 1
            except Exception:
                skipped += 1

    return imported, skipped


def get_bestiary_creature_count() -> int:
    if not BESTIARY_DIR.exists():
        return 0
    return len(list(BESTIARY_DIR.glob("*.md")))
