"""Creature / Spell / Item Database module.

Provides search/browse, bestiary import, and Gemini lookup with
confirm-before-save workflow.
"""

from __future__ import annotations

import json

import streamlit as st
from db import get_conn, jloads, jdumps


# ---------------------------------------------------------------------------
# DB helpers – Creatures
# ---------------------------------------------------------------------------

def _search_creatures(query: str = "", cr: str = "", creature_type: str = "") -> list[dict]:
    sql = "SELECT * FROM creatures WHERE 1=1"
    params: list = []
    if query:
        sql += " AND name LIKE ?"
        params.append(f"%{query}%")
    if cr:
        # Anchor to the start of the challenge string (e.g. "5 (1,800 XP)")
        # so CR 5 doesn't match XP values containing "5" or fractions like "1/4".
        sql += " AND (challenge = ? OR challenge LIKE ?)"
        params.extend([cr, f"{cr} (%"])
    if creature_type:
        sql += " AND (size LIKE ? OR tags LIKE ?)"
        params.extend([f"%{creature_type}%", f"%{creature_type}%"])
    sql += " ORDER BY name"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params)]


def _creature_count() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM creatures").fetchone()[0]


def _save_creature(data: dict) -> None:
    cols = [
        "name", "size", "alignment", "challenge", "hit_points", "armor_class", "speed",
        "str_score", "dex_score", "con_score", "int_score", "wis_score", "cha_score",
        "str_mod", "dex_mod", "con_mod", "int_mod", "wis_mod", "cha_mod",
        "skills", "saving_throws", "senses", "languages", "abilities", "source",
    ]
    vals = {c: data.get(c, "") for c in cols}
    update_set = ", ".join(f"{c}=excluded.{c}" for c in cols if c != "name")
    placeholders = ", ".join(f":{c}" for c in cols)
    col_list = ", ".join(cols)
    with get_conn() as conn:
        conn.execute(
            f"INSERT INTO creatures ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT(name) DO UPDATE SET {update_set}",
            vals,
        )


# ---------------------------------------------------------------------------
# DB helpers – Spells
# ---------------------------------------------------------------------------

def _search_spells(query: str = "", level: int | None = None, school: str = "") -> list[dict]:
    sql = "SELECT * FROM spells WHERE 1=1"
    params: list = []
    if query:
        sql += " AND name LIKE ?"
        params.append(f"%{query}%")
    if level is not None:
        sql += " AND level=?"
        params.append(level)
    if school:
        sql += " AND school LIKE ?"
        params.append(f"%{school}%")
    sql += " ORDER BY level, name"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params)]


def _save_spell(data: dict) -> None:
    cols = ["name", "level", "school", "casting_time", "range", "components",
            "duration", "description", "classes", "source"]
    vals = {c: data.get(c, "") for c in cols}
    update_set = ", ".join(f"{c}=excluded.{c}" for c in cols if c != "name")
    placeholders = ", ".join(f":{c}" for c in cols)
    col_list = ", ".join(cols)
    with get_conn() as conn:
        conn.execute(
            f"INSERT INTO spells ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT(name) DO UPDATE SET {update_set}",
            vals,
        )


# ---------------------------------------------------------------------------
# DB helpers – Items
# ---------------------------------------------------------------------------

def _search_items(query: str = "", item_type: str = "", rarity: str = "") -> list[dict]:
    sql = "SELECT * FROM items WHERE 1=1"
    params: list = []
    if query:
        sql += " AND name LIKE ?"
        params.append(f"%{query}%")
    if item_type:
        sql += " AND type LIKE ?"
        params.append(f"%{item_type}%")
    if rarity:
        sql += " AND rarity=?"
        params.append(rarity)
    sql += " ORDER BY name"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params)]


def _save_item(data: dict) -> None:
    cols = ["name", "type", "rarity", "description", "properties", "source"]
    vals = {c: data.get(c, "") for c in cols}
    if isinstance(vals.get("properties"), dict):
        vals["properties"] = jdumps(vals["properties"])
    update_set = ", ".join(f"{c}=excluded.{c}" for c in cols if c != "name")
    placeholders = ", ".join(f":{c}" for c in cols)
    col_list = ", ".join(cols)
    with get_conn() as conn:
        conn.execute(
            f"INSERT INTO items ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT(name) DO UPDATE SET {update_set}",
            vals,
        )


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

SPELL_SCHOOLS = [
    "", "Abjuration", "Conjuration", "Divination", "Enchantment",
    "Evocation", "Illusion", "Necromancy", "Transmutation",
]

RARITIES = ["", "common", "uncommon", "rare", "very rare", "legendary", "artifact"]

CREATURE_TYPES = [
    "", "aberration", "beast", "celestial", "construct", "dragon", "elemental",
    "fey", "fiend", "giant", "humanoid", "monstrosity", "ooze", "plant", "undead",
]


def _creature_card(c: dict) -> None:
    st.markdown(f"### {c['name']}")
    st.caption(f"{c['size']} · {c['alignment']} · CR {c['challenge']}")
    col1, col2 = st.columns(2)
    col1.write(f"**HP:** {c['hit_points']}  |  **AC:** {c['armor_class']}  |  **Speed:** {c['speed']}")
    col2.write(
        f"**STR** {c['str_score']}{c['str_mod']}  "
        f"**DEX** {c['dex_score']}{c['dex_mod']}  "
        f"**CON** {c['con_score']}{c['con_mod']}  "
        f"**INT** {c['int_score']}{c['int_mod']}  "
        f"**WIS** {c['wis_score']}{c['wis_mod']}  "
        f"**CHA** {c['cha_score']}{c['cha_mod']}"
    )
    if c.get("saving_throws"):
        st.write(f"**Saving Throws:** {c['saving_throws']}")
    if c.get("skills"):
        st.write(f"**Skills:** {c['skills']}")
    if c.get("senses"):
        st.write(f"**Senses:** {c['senses']}")
    if c.get("languages"):
        st.write(f"**Languages:** {c['languages']}")
    if c.get("abilities"):
        st.markdown(c["abilities"])


def _spell_card(s: dict) -> None:
    level_label = "Cantrip" if s["level"] == 0 else f"Level {s['level']}"
    st.markdown(f"### {s['name']}")
    st.caption(f"{level_label} · {s['school']}")
    st.write(
        f"**Casting Time:** {s['casting_time']}  |  "
        f"**Range:** {s['range']}  |  "
        f"**Duration:** {s['duration']}"
    )
    st.write(f"**Components:** {s['components']}")
    if s.get("classes"):
        st.write(f"**Classes:** {s['classes']}")
    st.write(s.get("description", ""))


def _item_card(item: dict) -> None:
    st.markdown(f"### {item['name']}")
    st.caption(f"{item['type']} · {item['rarity']}")
    st.write(item.get("description", ""))
    props = jloads(item.get("properties") or "{}")
    if props:
        for k, v in props.items():
            st.write(f"**{k}:** {v}")


# ---------------------------------------------------------------------------
# Gemini confirm-and-edit workflows
# ---------------------------------------------------------------------------

def _gemini_confirm_creature(data: dict) -> None:
    st.subheader("Review Gemini Result – Creature")
    st.info("Edit any fields before saving.")
    with st.form("gem_confirm_creature"):
        d = {}
        d["name"] = st.text_input("Name", value=str(data.get("name", "")))
        c1, c2 = st.columns(2)
        d["size"] = c1.text_input("Size", value=str(data.get("size", "")))
        d["alignment"] = c2.text_input("Alignment", value=str(data.get("alignment", "")))
        c3, c4, c5 = st.columns(3)
        d["challenge"] = c3.text_input("Challenge", value=str(data.get("challenge", "")))
        d["hit_points"] = c4.text_input("HP", value=str(data.get("hit_points", "")))
        d["armor_class"] = c5.text_input("AC", value=str(data.get("armor_class", "")))
        d["speed"] = st.text_input("Speed", value=str(data.get("speed", "")))
        ab_cols = st.columns(6)
        for i, ab in enumerate(["str", "dex", "con", "int", "wis", "cha"]):
            d[f"{ab}_score"] = ab_cols[i].number_input(
                ab.upper(), 1, 30, value=int(data.get(f"{ab}_score", 10))
            )
            d[f"{ab}_mod"] = f"({(d[f'{ab}_score'] - 10) // 2:+d})"
        d["skills"] = st.text_input("Skills", value=str(data.get("skills", "")))
        d["saving_throws"] = st.text_input("Saving Throws", value=str(data.get("saving_throws", "")))
        d["senses"] = st.text_input("Senses", value=str(data.get("senses", "")))
        d["languages"] = st.text_input("Languages", value=str(data.get("languages", "")))
        d["abilities"] = st.text_area("Abilities (Markdown)", value=str(data.get("abilities", "")), height=200)
        d["source"] = "Gemini"
        gc1, gc2 = st.columns(2)
        if gc1.form_submit_button("✅ Save Creature"):
            _save_creature(d)
            st.success(f"Saved **{d['name']}**")
            st.session_state.pop("gemini_creature_data", None)
            st.rerun()
        if gc2.form_submit_button("❌ Discard"):
            st.session_state.pop("gemini_creature_data", None)
            st.rerun()


def _gemini_confirm_spell(data: dict) -> None:
    st.subheader("Review Gemini Result – Spell")
    with st.form("gem_confirm_spell"):
        d = {}
        d["name"] = st.text_input("Name", value=str(data.get("name", "")))
        c1, c2 = st.columns(2)
        d["level"] = c1.number_input("Level (0=cantrip)", 0, 9, value=int(data.get("level", 0)))
        d["school"] = c2.text_input("School", value=str(data.get("school", "")))
        c3, c4, c5 = st.columns(3)
        d["casting_time"] = c3.text_input("Casting Time", value=str(data.get("casting_time", "")))
        d["range"] = c4.text_input("Range", value=str(data.get("range", "")))
        d["duration"] = c5.text_input("Duration", value=str(data.get("duration", "")))
        d["components"] = st.text_input("Components", value=str(data.get("components", "")))
        d["classes"] = st.text_input("Classes", value=str(data.get("classes", "")))
        d["description"] = st.text_area("Description", value=str(data.get("description", "")), height=150)
        d["source"] = "Gemini"
        sc1, sc2 = st.columns(2)
        if sc1.form_submit_button("✅ Save Spell"):
            _save_spell(d)
            st.success(f"Saved **{d['name']}**")
            st.session_state.pop("gemini_spell_data", None)
            st.rerun()
        if sc2.form_submit_button("❌ Discard"):
            st.session_state.pop("gemini_spell_data", None)
            st.rerun()


def _gemini_confirm_item(data: dict) -> None:
    st.subheader("Review Gemini Result – Item")
    with st.form("gem_confirm_item"):
        d = {}
        d["name"] = st.text_input("Name", value=str(data.get("name", "")))
        c1, c2 = st.columns(2)
        d["type"] = c1.text_input("Type", value=str(data.get("type", "")))
        d["rarity"] = c2.selectbox(
            "Rarity",
            ["common", "uncommon", "rare", "very rare", "legendary", "artifact"],
            index=["common", "uncommon", "rare", "very rare", "legendary", "artifact"].index(
                data.get("rarity", "common")
            ) if data.get("rarity") in ["common", "uncommon", "rare", "very rare", "legendary", "artifact"] else 0,
        )
        d["description"] = st.text_area("Description", value=str(data.get("description", "")), height=120)
        props = data.get("properties", {})
        if isinstance(props, str):
            try:
                props = json.loads(props)
            except Exception:
                props = {}
        d["properties"] = jdumps(props)
        d["source"] = "Gemini"
        ic1, ic2 = st.columns(2)
        if ic1.form_submit_button("✅ Save Item"):
            _save_item(d)
            st.success(f"Saved **{d['name']}**")
            st.session_state.pop("gemini_item_data", None)
            st.rerun()
        if ic2.form_submit_button("❌ Discard"):
            st.session_state.pop("gemini_item_data", None)
            st.rerun()


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_creature_database() -> None:
    st.header("📚 Creature / Spell / Item Database")

    tab_creature, tab_spell, tab_item = st.tabs(["🐉 Creatures", "✨ Spells", "⚔️ Items"])

    # ==== Creatures ====
    with tab_creature:
        # Import controls
        with st.expander("📥 Import from Bestiary", expanded=_creature_count() == 0):
            count = _creature_count()
            st.write(f"Currently **{count}** creatures in database.")
            if st.button("🔄 Import / Refresh All Bestiary Creatures", key="import_bestiary"):
                from utils.bestiary import import_all_creatures, get_bestiary_creature_count
                total = get_bestiary_creature_count()
                if total == 0:
                    st.warning("Bestiary submodule not found or empty.")
                else:
                    progress = st.progress(0.0, text="Importing…")
                    def _cb(pct, name):
                        progress.progress(pct, text=f"Importing {name}…")
                    imported, skipped = import_all_creatures(_cb)
                    progress.empty()
                    st.success(f"Imported {imported} creatures, skipped {skipped}.")
                    st.rerun()

        # Gemini lookup pending confirmation
        if st.session_state.get("gemini_creature_data"):
            _gemini_confirm_creature(st.session_state["gemini_creature_data"])
            st.divider()

        # Gemini lookup form
        with st.expander("🤖 Look Up Creature with Gemini"):
            from utils.gemini import is_initialised, lookup_creature
            if not is_initialised():
                st.warning("Configure Gemini API key in Settings.")
            else:
                gem_name = st.text_input("Creature name", key="gem_creature_name")
                if st.button("🔍 Fetch", key="gem_creature_fetch"):
                    with st.spinner(f"Fetching {gem_name}…"):
                        try:
                            result = lookup_creature(gem_name)
                            if result:
                                st.session_state["gemini_creature_data"] = result
                                st.rerun()
                            else:
                                st.error("Gemini returned no usable data.")
                        except Exception as e:
                            st.error(f"Gemini error: {e}")

        # Search + browse
        st.subheader("Search Creatures")
        sc1, sc2, sc3 = st.columns(3)
        c_query = sc1.text_input("Name", key="c_search")
        c_cr = sc2.text_input("CR (e.g. 10)", key="c_cr")
        c_type = sc3.selectbox("Type", CREATURE_TYPES, key="c_type")

        creatures = _search_creatures(c_query, c_cr, c_type)
        st.caption(f"{len(creatures)} result(s)")

        for c in creatures:
            with st.expander(f"**{c['name']}** – {c['size']} · CR {c['challenge']}"):
                _creature_card(c)

    # ==== Spells ====
    with tab_spell:
        if st.session_state.get("gemini_spell_data"):
            _gemini_confirm_spell(st.session_state["gemini_spell_data"])
            st.divider()

        with st.expander("🤖 Look Up Spell with Gemini"):
            from utils.gemini import is_initialised, lookup_spell
            if not is_initialised():
                st.warning("Configure Gemini API key in Settings.")
            else:
                gem_spell = st.text_input("Spell name", key="gem_spell_name")
                if st.button("🔍 Fetch", key="gem_spell_fetch"):
                    with st.spinner(f"Fetching {gem_spell}…"):
                        try:
                            result = lookup_spell(gem_spell)
                            if result:
                                st.session_state["gemini_spell_data"] = result
                                st.rerun()
                            else:
                                st.error("Gemini returned no usable data.")
                        except Exception as e:
                            st.error(f"Gemini error: {e}")

        st.subheader("Search Spells")
        ss1, ss2, ss3 = st.columns(3)
        s_query = ss1.text_input("Name", key="s_search")
        s_level_str = ss2.selectbox("Level", ["Any"] + [str(i) for i in range(10)], key="s_level")
        s_level = None if s_level_str == "Any" else int(s_level_str)
        s_school = ss3.selectbox("School", SPELL_SCHOOLS, key="s_school")

        spells = _search_spells(s_query, s_level, s_school)
        st.caption(f"{len(spells)} result(s)")

        for s in spells:
            level_label = "Cantrip" if s["level"] == 0 else f"L{s['level']}"
            with st.expander(f"**{s['name']}** – {level_label} {s['school']}"):
                _spell_card(s)

    # ==== Items ====
    with tab_item:
        if st.session_state.get("gemini_item_data"):
            _gemini_confirm_item(st.session_state["gemini_item_data"])
            st.divider()

        with st.expander("🤖 Look Up Item with Gemini"):
            from utils.gemini import is_initialised, lookup_item
            if not is_initialised():
                st.warning("Configure Gemini API key in Settings.")
            else:
                gem_item = st.text_input("Item name", key="gem_item_name")
                if st.button("🔍 Fetch", key="gem_item_fetch"):
                    with st.spinner(f"Fetching {gem_item}…"):
                        try:
                            result = lookup_item(gem_item)
                            if result:
                                st.session_state["gemini_item_data"] = result
                                st.rerun()
                            else:
                                st.error("Gemini returned no usable data.")
                        except Exception as e:
                            st.error(f"Gemini error: {e}")

        st.subheader("Search Items")
        si1, si2, si3 = st.columns(3)
        i_query = si1.text_input("Name", key="i_search")
        i_type = si2.text_input("Type", key="i_type")
        i_rarity = si3.selectbox("Rarity", RARITIES, key="i_rarity")

        items = _search_items(i_query, i_type, i_rarity)
        st.caption(f"{len(items)} result(s)")

        for item in items:
            with st.expander(f"**{item['name']}** – {item['type']} ({item['rarity']})"):
                _item_card(item)
