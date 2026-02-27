"""Encounter Builder – initiative tracking, HP management, and Gemini suggestions."""

from __future__ import annotations

import random
from copy import deepcopy

import streamlit as st
from db import get_conn, jloads, jdumps


def _get_characters() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, ability_scores, hp_max, hp_current, ac, initiative_bonus "
            "FROM characters ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


def _get_creatures_summary() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, hit_points, armor_class, challenge FROM creatures ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


def _parse_hp(hp_str: str) -> int:
    """Parse a hit_points string like '135 (18d10+36)' and return the integer."""
    import re
    m = re.match(r"(\d+)", str(hp_str))
    return int(m.group(1)) if m else 0


def _parse_ac(ac_str: str) -> int:
    import re
    m = re.match(r"(\d+)", str(ac_str))
    return int(m.group(1)) if m else 10


def _dex_mod(ability_scores_json: str | None) -> int:
    scores = jloads(ability_scores_json or "{}")
    dex = scores.get("DEX", 10)
    return (int(dex) - 10) // 2


def _init_encounter_state() -> None:
    if "enc_participants" not in st.session_state:
        st.session_state["enc_participants"] = []
    if "enc_round" not in st.session_state:
        st.session_state["enc_round"] = 1
    if "enc_active_idx" not in st.session_state:
        st.session_state["enc_active_idx"] = 0
    if "enc_notes" not in st.session_state:
        st.session_state["enc_notes"] = ""


def render_encounter_builder() -> None:
    st.header("⚔️ Encounter Builder")
    _init_encounter_state()

    tab_setup, tab_run, tab_gemini = st.tabs(["🏗️ Setup", "▶️ Run Encounter", "🤖 Gemini Suggestions"])

    # ---- Setup tab ----
    with tab_setup:
        st.subheader("Add Participants")

        add_type = st.radio("Add from", ["Character", "Bestiary Creature", "Custom"],
                            horizontal=True, key="enc_add_type")

        if add_type == "Character":
            chars = _get_characters()
            if not chars:
                st.info("No characters in database.")
            else:
                sel = st.selectbox("Character", chars,
                                   format_func=lambda c: c["name"],
                                   key="enc_char_sel")
                if st.button("➕ Add Character", key="enc_add_char"):
                    dex_m = _dex_mod(sel.get("ability_scores"))
                    st.session_state["enc_participants"].append({
                        "name": sel["name"],
                        "type": "character",
                        "hp_max": int(sel.get("hp_max", 0)),
                        "hp_current": int(sel.get("hp_current", 0)),
                        "ac": int(sel.get("ac", 10)),
                        "initiative": dex_m + random.randint(1, 20),
                        "initiative_bonus": dex_m,
                        "status": "alive",
                    })
                    st.success(f"Added {sel['name']}")
                    st.rerun()

        elif add_type == "Bestiary Creature":
            creatures = _get_creatures_summary()
            if not creatures:
                st.info("No creatures imported. Visit the Creature Database to import the bestiary.")
            else:
                sel = st.selectbox("Creature", creatures,
                                   format_func=lambda c: f"{c['name']} (CR {c['challenge']})",
                                   key="enc_creature_sel")
                count = st.number_input("# to add", 1, 20, 1, key="enc_creature_count")
                if st.button("➕ Add Creature(s)", key="enc_add_creature"):
                    for i in range(int(count)):
                        label = sel["name"] if count == 1 else f"{sel['name']} {i+1}"
                        hp = _parse_hp(sel.get("hit_points", "0"))
                        ac = _parse_ac(sel.get("armor_class", "10"))
                        st.session_state["enc_participants"].append({
                            "name": label,
                            "type": "creature",
                            "hp_max": hp,
                            "hp_current": hp,
                            "ac": ac,
                            "initiative": random.randint(1, 20),
                            "initiative_bonus": 0,
                            "status": "alive",
                        })
                    st.success(f"Added {count} × {sel['name']}")
                    st.rerun()

        else:  # Custom
            with st.form("enc_custom_form"):
                cn1, cn2 = st.columns(2)
                custom_name = cn1.text_input("Name")
                custom_hp = cn2.number_input("Max HP", 1, 999, 10)
                cn3, cn4 = st.columns(2)
                custom_ac = cn3.number_input("AC", 1, 30, 10)
                custom_init = cn4.number_input("Initiative", -5, 30, 10)
                if st.form_submit_button("➕ Add Custom"):
                    if custom_name:
                        st.session_state["enc_participants"].append({
                            "name": custom_name,
                            "type": "custom",
                            "hp_max": int(custom_hp),
                            "hp_current": int(custom_hp),
                            "ac": int(custom_ac),
                            "initiative": int(custom_init),
                            "initiative_bonus": 0,
                            "status": "alive",
                        })
                        st.success(f"Added {custom_name}")
                        st.rerun()

        st.divider()
        participants = st.session_state["enc_participants"]
        if participants:
            st.subheader("Current Participants")
            for i, p in enumerate(participants):
                pc1, pc2, pc3 = st.columns([3, 2, 1])
                pc1.write(f"**{p['name']}** (init {p['initiative']}, HP {p['hp_current']}/{p['hp_max']}, AC {p['ac']})")
                new_init = pc2.number_input("Initiative", -5, 40, value=p["initiative"],
                                             key=f"enc_init_{i}", label_visibility="collapsed")
                participants[i]["initiative"] = int(new_init)
                if pc3.button("🗑️", key=f"enc_rm_{i}"):
                    st.session_state["enc_participants"].pop(i)
                    st.rerun()

            col_sort, col_reset = st.columns(2)
            if col_sort.button("🔀 Sort by Initiative", key="enc_sort"):
                st.session_state["enc_participants"].sort(
                    key=lambda p: p["initiative"], reverse=True
                )
                st.session_state["enc_active_idx"] = 0
                st.rerun()
            if col_reset.button("🗑️ Clear Encounter", key="enc_clear"):
                st.session_state["enc_participants"] = []
                st.session_state["enc_round"] = 1
                st.session_state["enc_active_idx"] = 0
                st.rerun()

    # ---- Run tab ----
    with tab_run:
        participants = st.session_state["enc_participants"]
        if not participants:
            st.info("Add participants in the Setup tab first.")
        else:
            round_num = st.session_state["enc_round"]
            active_idx = st.session_state["enc_active_idx"] % len(participants)
            st.session_state["enc_active_idx"] = active_idx

            st.subheader(f"Round {round_num}")
            active = participants[active_idx]
            st.info(f"🎯 Active: **{active['name']}** (Initiative {active['initiative']})")

            nc1, nc2 = st.columns(2)
            if nc1.button("⏭️ Next Turn", key="enc_next", use_container_width=True, type="primary"):
                next_idx = (active_idx + 1) % len(participants)
                if next_idx == 0:
                    st.session_state["enc_round"] += 1
                st.session_state["enc_active_idx"] = next_idx
                st.rerun()
            if nc2.button("🔁 Reset Round Counter", key="enc_reset_round"):
                st.session_state["enc_round"] = 1
                st.rerun()

            st.divider()
            st.subheader("HP Tracker")
            for i, p in enumerate(participants):
                status_emoji = {"alive": "🟢", "unconscious": "🟡", "dead": "💀"}.get(p["status"], "🟢")
                active_marker = "▶️ " if i == active_idx else ""
                row = st.columns([3, 2, 2, 2, 2])
                row[0].write(f"{active_marker}{status_emoji} **{p['name']}** (AC {p['ac']})")

                hp_change = row[1].number_input(
                    "HP Δ", -999, 999, 0, key=f"enc_hpd_{i}", label_visibility="collapsed"
                )
                if row[2].button("Apply", key=f"enc_apply_{i}"):
                    participants[i]["hp_current"] = max(
                        0, min(p["hp_max"], p["hp_current"] + int(hp_change))
                    )
                    if participants[i]["hp_current"] == 0:
                        participants[i]["status"] = "unconscious"
                    elif participants[i]["hp_current"] > 0 and p["status"] == "unconscious":
                        participants[i]["status"] = "alive"
                    st.rerun()

                row[3].progress(
                    p["hp_current"] / max(p["hp_max"], 1),
                    text=f"{p['hp_current']}/{p['hp_max']}",
                )

                status_options = ["alive", "unconscious", "dead"]
                cur_status_idx = status_options.index(p.get("status", "alive"))
                new_status = row[4].selectbox(
                    "Status", status_options, index=cur_status_idx,
                    key=f"enc_status_{i}", label_visibility="collapsed"
                )
                participants[i]["status"] = new_status

            st.divider()
            st.subheader("Notes")
            st.session_state["enc_notes"] = st.text_area(
                "Encounter notes", value=st.session_state["enc_notes"],
                key="enc_notes_input", height=100
            )

    # ---- Gemini tab ----
    with tab_gemini:
        from utils.gemini import is_initialised, encounter_suggestions

        participants = st.session_state["enc_participants"]
        if not participants:
            st.info("Add participants first.")
        elif not is_initialised():
            st.warning("Gemini API not configured. Add your API key in Settings.")
        else:
            st.write("Get tactical advice and narrative suggestions from Gemini.")
            notes = st.text_area("Additional context", height=80, key="enc_gemini_ctx")
            if st.button("🤖 Get Suggestions", key="enc_gemini_btn", type="primary"):
                with st.spinner("Asking Gemini…"):
                    try:
                        result = encounter_suggestions(participants, notes)
                        st.session_state["enc_gemini_result"] = result
                    except Exception as e:
                        st.error(f"Gemini error: {e}")

            if st.session_state.get("enc_gemini_result"):
                st.markdown(st.session_state["enc_gemini_result"])
