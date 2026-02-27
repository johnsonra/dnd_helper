"""Character Sheet module – create, edit, view, and delete characters."""

from __future__ import annotations

import json
import streamlit as st
from db import get_conn, jloads, jdumps

# ---------------------------------------------------------------------------
# D&D 5e constants
# ---------------------------------------------------------------------------

ABILITIES = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
DB_COLS = ["str", "dex", "con", "int", "wis", "cha"]

SKILLS = [
    ("Acrobatics", "DEX"), ("Animal Handling", "WIS"), ("Arcana", "INT"),
    ("Athletics", "STR"), ("Deception", "CHA"), ("History", "INT"),
    ("Insight", "WIS"), ("Intimidation", "CHA"), ("Investigation", "INT"),
    ("Medicine", "WIS"), ("Nature", "INT"), ("Perception", "WIS"),
    ("Performance", "CHA"), ("Persuasion", "CHA"), ("Religion", "INT"),
    ("Sleight of Hand", "DEX"), ("Stealth", "DEX"), ("Survival", "WIS"),
]

CLASSES = [
    "Artificer", "Barbarian", "Bard", "Cleric", "Druid", "Fighter",
    "Monk", "NPC/Monster", "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard",
]

ALIGNMENTS = [
    "Lawful Good", "Neutral Good", "Chaotic Good",
    "Lawful Neutral", "True Neutral", "Chaotic Neutral",
    "Lawful Evil", "Neutral Evil", "Chaotic Evil", "Unaligned",
]

SPELL_SCHOOLS = [
    "Abjuration", "Conjuration", "Divination", "Enchantment",
    "Evocation", "Illusion", "Necromancy", "Transmutation",
]

PROF_BONUS = {1: 2, 2: 2, 3: 2, 4: 2, 5: 3, 6: 3, 7: 3, 8: 3,
              9: 4, 10: 4, 11: 4, 12: 4, 13: 5, 14: 5, 15: 5, 16: 5,
              17: 6, 18: 6, 19: 6, 20: 6}

SPELL_SLOT_TABLE: dict[int, dict[int, int]] = {
    # level: {slot_level: count}
    1:  {1: 2},
    2:  {1: 3},
    3:  {1: 4, 2: 2},
    4:  {1: 4, 2: 3},
    5:  {1: 4, 2: 3, 3: 2},
    6:  {1: 4, 2: 3, 3: 3},
    7:  {1: 4, 2: 3, 3: 3, 4: 1},
    8:  {1: 4, 2: 3, 3: 3, 4: 2},
    9:  {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
    10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
    11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    12: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    14: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    16: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
    18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 1, 7: 1, 8: 1, 9: 1},
    19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 1, 8: 1, 9: 1},
    20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1},
}


def _mod(score: int) -> int:
    return (score - 10) // 2


def _mod_str(score: int) -> str:
    m = _mod(score)
    return f"+{m}" if m >= 0 else str(m)


def _prof_bonus(level: int) -> int:
    return PROF_BONUS.get(level, 2)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_campaigns() -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT id, name FROM campaigns ORDER BY name")]


def _get_characters(campaign_id: int | None = None) -> list[dict]:
    with get_conn() as conn:
        if campaign_id:
            rows = conn.execute(
                "SELECT * FROM characters WHERE campaign_id=? ORDER BY name", (campaign_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM characters ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def _save_character(data: dict, char_id: int | None = None) -> int:
    cols = [
        "campaign_id", "name", "player_name", "race", "class", "subclass", "level",
        "background", "alignment", "xp", "ability_scores", "save_profs", "skill_profs",
        "hp_max", "hp_current", "hp_temp", "ac", "speed", "initiative_bonus",
        "features", "equipment", "currency", "spells", "spell_slots", "notes",
    ]
    with get_conn() as conn:
        if char_id:
            set_clause = ", ".join(f"{c}=:{c}" for c in cols)
            data["id"] = char_id
            conn.execute(
                f"UPDATE characters SET {set_clause}, updated_at=datetime('now') WHERE id=:id",
                data,
            )
            return char_id
        else:
            placeholders = ", ".join(f":{c}" for c in cols)
            col_list = ", ".join(cols)
            cur = conn.execute(
                f"INSERT INTO characters ({col_list}) VALUES ({placeholders})", data
            )
            return cur.lastrowid


def _delete_character(char_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM characters WHERE id=?", (char_id,))


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _stat_block(scores: dict) -> None:
    """Render the six ability score boxes."""
    cols = st.columns(6)
    for i, ability in enumerate(ABILITIES):
        sc = scores.get(ability, 10)
        with cols[i]:
            st.metric(ability, sc, _mod_str(sc))


def _skill_table(scores: dict, skill_profs: list, save_profs: list, level: int) -> None:
    pb = _prof_bonus(level)
    st.subheader("Saving Throws")
    save_cols = st.columns(3)
    for i, ab in enumerate(ABILITIES):
        sc = scores.get(ab, 10)
        base = _mod(sc)
        prof = "✅" if ab in save_profs else "◻️"
        bonus = base + (pb if ab in save_profs else 0)
        save_cols[i % 3].write(f"{prof} **{ab}** {bonus:+d}")

    st.subheader("Skills")
    skl_cols = st.columns(2)
    for i, (skill, ab) in enumerate(SKILLS):
        sc = scores.get(ab, 10)
        base = _mod(sc)
        prof = "✅" if skill in skill_profs else "◻️"
        bonus = base + (pb if skill in skill_profs else 0)
        skl_cols[i % 2].write(f"{prof} **{skill}** ({ab}) {bonus:+d}")


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_character_sheet() -> None:
    st.header("🧙 Character Sheet")

    # If a creature NPC template was loaded from the Database tab, show a banner.
    npc_template = st.session_state.get("npc_template")
    if npc_template:
        st.info(
            f"🧑 NPC template loaded from **{npc_template['name']}**. "
            "Open the **➕ New** tab below to review and save."
        )

    tab_list, tab_view, tab_edit, tab_new = st.tabs(
        ["📋 Characters", "👁️ View", "✏️ Edit", "➕ New"]
    )

    # ---- Character list ----
    with tab_list:
        chars = _get_characters()
        if not chars:
            st.info("No characters yet. Create one in the **New** tab.")
        else:
            for c in chars:
                cols = st.columns([3, 1, 1, 1])
                cols[0].write(
                    f"**{c['name']}** – {c['class']} {c['level']} ({c['race']})"
                )
                if cols[1].button("View", key=f"view_{c['id']}"):
                    st.session_state["active_char_id"] = c["id"]
                    st.rerun()
                if cols[2].button("Edit", key=f"edit_{c['id']}"):
                    st.session_state["edit_char_id"] = c["id"]
                    st.rerun()
                if cols[3].button("🗑️", key=f"del_{c['id']}"):
                    _delete_character(c["id"])
                    st.success(f"Deleted {c['name']}")
                    st.rerun()

    # ---- View character ----
    with tab_view:
        chars = _get_characters()
        char_names = {c["id"]: c["name"] for c in chars}
        if not chars:
            st.info("No characters yet.")
        else:
            default_id = st.session_state.get("active_char_id", chars[0]["id"])
            sel = st.selectbox(
                "Character",
                options=[c["id"] for c in chars],
                format_func=lambda x: char_names.get(x, str(x)),
                key="view_char_sel",
                index=next((i for i, c in enumerate(chars) if c["id"] == default_id), 0),
            )
            with get_conn() as conn:
                row = conn.execute("SELECT * FROM characters WHERE id=?", (sel,)).fetchone()
            if row:
                c = dict(row)
                scores = jloads(c.get("ability_scores") or "{}")

                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader(c["name"])
                    st.caption(
                        f"{c['race']} · {c['class']} {c['level']} · {c['background']} · {c['alignment']}"
                    )
                    st.write(f"**Player:** {c['player_name']}  |  **XP:** {c['xp']}")
                    pb = _prof_bonus(c["level"])
                    st.write(
                        f"**Proficiency Bonus:** +{pb}  |  **Initiative:** {_mod_str(scores.get('DEX', 10))}  |  **Speed:** {c['speed']} ft."
                    )

                with col2:
                    hcol1, hcol2, hcol3 = st.columns(3)
                    hcol1.metric("AC", c["ac"])
                    hcol2.metric("HP", f"{c['hp_current']}/{c['hp_max']}")
                    hcol3.metric("Temp HP", c["hp_temp"])

                st.divider()
                _stat_block(scores)
                st.divider()
                save_profs = jloads(c.get("save_profs") or "[]")
                skill_profs = jloads(c.get("skill_profs") or "[]")
                _skill_table(scores, skill_profs, save_profs, c["level"])

                st.divider()
                feat_col, equip_col = st.columns(2)
                with feat_col:
                    st.subheader("Features & Traits")
                    for f in jloads(c.get("features") or "[]"):
                        st.write(f"• {f}")

                with equip_col:
                    st.subheader("Equipment")
                    for item in jloads(c.get("equipment") or "[]"):
                        st.write(f"• {item}")
                    cur = jloads(c.get("currency") or "{}")
                    st.write(
                        f"💰 {cur.get('pp',0)}pp · {cur.get('gp',0)}gp · "
                        f"{cur.get('ep',0)}ep · {cur.get('sp',0)}sp · {cur.get('cp',0)}cp"
                    )

                spells = jloads(c.get("spells") or "{}")
                if spells:
                    st.divider()
                    st.subheader("Spells")
                    for lvl in sorted(spells.keys(), key=int):
                        label = "Cantrips" if int(lvl) == 0 else f"Level {lvl}"
                        st.write(f"**{label}:** " + ", ".join(spells[lvl]))

                if c.get("notes"):
                    st.divider()
                    st.subheader("Notes")
                    st.write(c["notes"])

    # ---- Edit character ----
    with tab_edit:
        chars = _get_characters()
        if not chars:
            st.info("No characters yet.")
        else:
            default_edit = st.session_state.get("edit_char_id", chars[0]["id"])
            sel = st.selectbox(
                "Character to edit",
                options=[c["id"] for c in chars],
                format_func=lambda x: next((c["name"] for c in chars if c["id"] == x), str(x)),
                key="edit_char_sel",
                index=next((i for i, c in enumerate(chars) if c["id"] == default_edit), 0),
            )
            with get_conn() as conn:
                row = conn.execute("SELECT * FROM characters WHERE id=?", (sel,)).fetchone()
            if row:
                _render_character_form(dict(row), char_id=sel)

    # ---- New character ----
    with tab_new:
        npc_template = st.session_state.get("npc_template")
        _render_character_form(None, char_id=None, npc_template=npc_template)


def _render_character_form(existing: dict | None, char_id: int | None,
                           npc_template: dict | None = None) -> None:
    """Shared form for creating or editing a character.

    When *npc_template* is provided (new character only), its values pre-fill
    the form fields so the user can review and tweak before saving.
    """
    prefix = f"char_{char_id or 'new'}_"
    e = existing or {}

    # Merge NPC template into defaults for new characters
    if npc_template and not existing:
        e = {
            "name":           npc_template.get("name", ""),
            "race":           npc_template.get("race", ""),
            "class":          "NPC/Monster",
            "hp_max":         npc_template.get("hp_max", 0),
            "hp_current":     npc_template.get("hp_current", 0),
            "ac":             npc_template.get("ac", 10),
            "speed":          npc_template.get("speed", 30),
            "ability_scores": jdumps(npc_template.get("ability_scores", {})),
            "notes":          npc_template.get("notes", ""),
        }

    scores = jloads(e.get("ability_scores") or "{}")
    save_profs_existing = jloads(e.get("save_profs") or "[]")
    skill_profs_existing = jloads(e.get("skill_profs") or "[]")
    features_existing = "\n".join(jloads(e.get("features") or "[]"))
    equipment_existing = "\n".join(jloads(e.get("equipment") or "[]"))
    cur = jloads(e.get("currency") or '{"pp":0,"gp":0,"ep":0,"sp":0,"cp":0}')

    with st.form(key=f"{prefix}form"):
        st.subheader("Basic Info")
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Character Name *", value=e.get("name", ""))
        player = c2.text_input("Player Name", value=e.get("player_name", ""))
        race = c3.text_input("Race", value=e.get("race", ""))

        c4, c5, c6 = st.columns(3)
        cls_idx = CLASSES.index(e["class"]) if e.get("class") in CLASSES else 0
        char_class = c4.selectbox("Class", CLASSES, index=cls_idx, key=f"{prefix}cls")
        subclass = c5.text_input("Subclass", value=e.get("subclass", ""))
        level = c6.number_input("Level", 1, 20, value=int(e.get("level", 1)))

        c7, c8, c9 = st.columns(3)
        background = c7.text_input("Background", value=e.get("background", ""))
        aln_idx = ALIGNMENTS.index(e["alignment"]) if e.get("alignment") in ALIGNMENTS else 0
        alignment = c8.selectbox("Alignment", ALIGNMENTS, index=aln_idx, key=f"{prefix}aln")
        xp = c9.number_input("XP", 0, 355000, value=int(e.get("xp", 0)))

        # Campaign assignment
        campaigns = _get_campaigns()
        campaign_options = [None] + [c["id"] for c in campaigns]
        campaign_labels = ["(none)"] + [c["name"] for c in campaigns]
        cur_cid = e.get("campaign_id")
        cid_idx = campaign_options.index(cur_cid) if cur_cid in campaign_options else 0
        campaign_id = st.selectbox(
            "Campaign", campaign_options, format_func=lambda x: campaign_labels[campaign_options.index(x)],
            index=cid_idx, key=f"{prefix}camp"
        )

        st.divider()
        st.subheader("Ability Scores")
        ab_cols = st.columns(6)
        new_scores: dict[str, int] = {}
        for i, ab in enumerate(ABILITIES):
            new_scores[ab] = ab_cols[i].number_input(
                ab, 1, 30, value=int(scores.get(ab, 10)), key=f"{prefix}ab_{ab}"
            )

        st.divider()
        st.subheader("Combat")
        cc1, cc2, cc3, cc4 = st.columns(4)
        hp_max = cc1.number_input("Max HP", 1, 999, value=int(e.get("hp_max", 8)))
        hp_current = cc2.number_input("Current HP", 0, 999, value=int(e.get("hp_current", 8)))
        hp_temp = cc3.number_input("Temp HP", 0, 999, value=int(e.get("hp_temp", 0)))
        ac = cc4.number_input("AC", 1, 30, value=int(e.get("ac", 10)))
        cc5, cc6 = st.columns(2)
        speed = cc5.number_input("Speed (ft)", 0, 120, value=int(e.get("speed", 30)), step=5)
        init_bonus = cc6.number_input(
            "Initiative Bonus (override)", -10, 20, value=int(e.get("initiative_bonus", 0))
        )

        st.divider()
        st.subheader("Proficiencies")
        save_profs = st.multiselect("Saving Throw Proficiencies", ABILITIES, default=save_profs_existing)
        skill_profs = st.multiselect(
            "Skill Proficiencies", [s for s, _ in SKILLS], default=skill_profs_existing
        )

        st.divider()
        st.subheader("Features & Traits")
        features_text = st.text_area(
            "One per line", value=features_existing, height=100, key=f"{prefix}feats"
        )

        st.subheader("Equipment")
        equipment_text = st.text_area(
            "One item per line", value=equipment_existing, height=100, key=f"{prefix}equip"
        )

        st.subheader("Currency")
        cu1, cu2, cu3, cu4, cu5 = st.columns(5)
        pp = cu1.number_input("PP", 0, value=int(cur.get("pp", 0)), key=f"{prefix}pp")
        gp = cu2.number_input("GP", 0, value=int(cur.get("gp", 0)), key=f"{prefix}gp")
        ep = cu3.number_input("EP", 0, value=int(cur.get("ep", 0)), key=f"{prefix}ep")
        sp = cu4.number_input("SP", 0, value=int(cur.get("sp", 0)), key=f"{prefix}sp")
        cp = cu5.number_input("CP", 0, value=int(cur.get("cp", 0)), key=f"{prefix}cp")

        st.subheader("Notes")
        notes = st.text_area("Campaign notes, backstory…", value=e.get("notes", ""), height=100)

        submitted = st.form_submit_button("💾 Save Character")

    if submitted:
        if not name:
            st.error("Character name is required.")
            return

        payload = {
            "campaign_id": campaign_id,
            "name": name,
            "player_name": player,
            "race": race,
            "class": char_class,
            "subclass": subclass,
            "level": level,
            "background": background,
            "alignment": alignment,
            "xp": xp,
            "ability_scores": jdumps(new_scores),
            "save_profs": jdumps(save_profs),
            "skill_profs": jdumps(skill_profs),
            "hp_max": hp_max,
            "hp_current": hp_current,
            "hp_temp": hp_temp,
            "ac": ac,
            "speed": speed,
            "initiative_bonus": init_bonus,
            "features": jdumps([f.strip() for f in features_text.splitlines() if f.strip()]),
            "equipment": jdumps([f.strip() for f in equipment_text.splitlines() if f.strip()]),
            "currency": jdumps({"pp": pp, "gp": gp, "ep": ep, "sp": sp, "cp": cp}),
            "spells": e.get("spells", "{}"),
            "spell_slots": e.get("spell_slots", "{}"),
            "notes": notes,
        }
        new_id = _save_character(payload, char_id=char_id)
        st.session_state["active_char_id"] = new_id
        # Clear any NPC template that was used to pre-fill this form
        st.session_state.pop("npc_template", None)
        st.success(f"✅ Character **{name}** saved!")
        st.rerun()
