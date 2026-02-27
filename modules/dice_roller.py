"""Dice Roller module – roll dice with modifiers, advantage/disadvantage,
roll history, and quick-roll buttons tied to a selected character."""

from __future__ import annotations

import random
from collections import deque

import streamlit as st
from db import get_conn, jloads

DICE = [4, 6, 8, 10, 12, 20, 100]
MAX_HISTORY = 50

SKILLS = [
    ("Acrobatics", "DEX"), ("Animal Handling", "WIS"), ("Arcana", "INT"),
    ("Athletics", "STR"), ("Deception", "CHA"), ("History", "INT"),
    ("Insight", "WIS"), ("Intimidation", "CHA"), ("Investigation", "INT"),
    ("Medicine", "WIS"), ("Nature", "INT"), ("Perception", "WIS"),
    ("Performance", "CHA"), ("Persuasion", "CHA"), ("Religion", "INT"),
    ("Sleight of Hand", "DEX"), ("Stealth", "DEX"), ("Survival", "WIS"),
]

ABILITIES = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

PROF_BONUS = {1: 2, 2: 2, 3: 2, 4: 2, 5: 3, 6: 3, 7: 3, 8: 3,
              9: 4, 10: 4, 11: 4, 12: 4, 13: 5, 14: 5, 15: 5, 16: 5,
              17: 6, 18: 6, 19: 6, 20: 6}


def _mod(score: int) -> int:
    return (score - 10) // 2


def _roll(sides: int, count: int = 1) -> list[int]:
    return [random.randint(1, sides) for _ in range(count)]


def _add_history(entry: str) -> None:
    if "roll_history" not in st.session_state:
        st.session_state["roll_history"] = deque(maxlen=MAX_HISTORY)
    st.session_state["roll_history"].appendleft(entry)


def _do_roll(label: str, dice_count: int, sides: int, modifier: int,
             advantage: bool, disadvantage: bool) -> None:
    if advantage or disadvantage:
        roll1 = _roll(sides, dice_count)
        roll2 = _roll(sides, dice_count)
        s1, s2 = sum(roll1), sum(roll2)
        if advantage:
            chosen, other = (roll1, roll2) if s1 >= s2 else (roll2, roll1)
            mode = "Adv"
        else:
            chosen, other = (roll1, roll2) if s1 <= s2 else (roll2, roll1)
            mode = "Dis"
        total = sum(chosen) + modifier
        entry = (
            f"**{label}** [{mode}] → **{total}** "
            f"(took {chosen}, dropped {other}, mod {modifier:+d})"
        )
    else:
        rolls = _roll(sides, dice_count)
        total = sum(rolls) + modifier
        entry = (
            f"**{label}** → **{total}** "
            f"({dice_count}d{sides}: {rolls}, mod {modifier:+d})"
        )

    st.session_state["last_roll"] = entry
    _add_history(entry)


def render_dice_roller() -> None:
    st.header("🎲 Dice Roller")

    left, right = st.columns([2, 1])

    # ---- Main roller ----
    with left:
        st.subheader("Standard Roll")
        rc1, rc2, rc3 = st.columns(3)
        dice_count = rc1.number_input("# of Dice", 1, 20, value=1, key="dr_count")
        dice_type = rc2.selectbox("Die Type", DICE, index=5, key="dr_type",
                                  format_func=lambda x: f"d{x}")
        modifier = rc3.number_input("Modifier", -20, 20, value=0, key="dr_mod")

        adv_col, dis_col = st.columns(2)
        advantage = adv_col.checkbox("Advantage", key="dr_adv")
        disadvantage = dis_col.checkbox("Disadvantage", key="dr_dis")

        if st.button(f"🎲 Roll {dice_count}d{dice_type} {modifier:+d}", key="dr_roll",
                     use_container_width=True, type="primary"):
            _do_roll(
                f"{dice_count}d{dice_type}",
                dice_count, dice_type, modifier,
                advantage, disadvantage,
            )

        if st.session_state.get("last_roll"):
            st.success(st.session_state["last_roll"])

        st.divider()

        # Quick dice buttons
        st.subheader("Quick Roll (1 die, no modifier)")
        qcols = st.columns(len(DICE))
        for i, d in enumerate(DICE):
            if qcols[i].button(f"d{d}", key=f"qr_{d}", use_container_width=True):
                _do_roll(f"d{d}", 1, d, 0, False, False)
                st.rerun()

    # ---- Character quick rolls ----
    with right:
        st.subheader("Character Quick Rolls")
        with get_conn() as conn:
            chars = [dict(r) for r in conn.execute(
                "SELECT id, name, class, level, ability_scores, save_profs, skill_profs, initiative_bonus "
                "FROM characters ORDER BY name"
            )]
        if not chars:
            st.info("No characters. Create one in Character Sheet.")
        else:
            sel = st.selectbox("Character", chars,
                               format_func=lambda c: f"{c['name']} (Lvl {c['level']})",
                               key="dr_char_sel")
            if sel:
                c = sel
                scores = jloads(c.get("ability_scores") or "{}")
                pb = PROF_BONUS.get(int(c.get("level", 1)), 2)
                save_profs = jloads(c.get("save_profs") or "[]")
                skill_profs = jloads(c.get("skill_profs") or "[]")

                st.write("**Ability Checks**")
                ab_cols = st.columns(3)
                for i, ab in enumerate(ABILITIES):
                    m = _mod(scores.get(ab, 10))
                    label = f"{ab} {m:+d}"
                    if ab_cols[i % 3].button(label, key=f"qr_ab_{ab}", use_container_width=True):
                        _do_roll(f"{c['name']} {ab} check", 1, 20, m, False, False)
                        st.rerun()

                st.write("**Saving Throws**")
                sv_cols = st.columns(3)
                for i, ab in enumerate(ABILITIES):
                    m = _mod(scores.get(ab, 10))
                    total = m + (pb if ab in save_profs else 0)
                    label = f"{ab} {total:+d}"
                    if sv_cols[i % 3].button(label, key=f"qr_sv_{ab}", use_container_width=True):
                        _do_roll(f"{c['name']} {ab} save", 1, 20, total, False, False)
                        st.rerun()

                st.write("**Skills**")
                for skill, ab in SKILLS:
                    m = _mod(scores.get(ab, 10))
                    total = m + (pb if skill in skill_profs else 0)
                    prof_marker = "✅" if skill in skill_profs else "◻️"
                    if st.button(
                        f"{prof_marker} {skill} {total:+d}",
                        key=f"qr_sk_{skill.replace(' ','_')}",
                        use_container_width=True
                    ):
                        _do_roll(f"{c['name']} {skill}", 1, 20, total, False, False)
                        st.rerun()

    # ---- Roll history ----
    st.divider()
    st.subheader("📜 Roll History")
    if st.button("Clear History", key="clear_hist"):
        st.session_state["roll_history"] = deque(maxlen=MAX_HISTORY)
        st.rerun()
    history = list(st.session_state.get("roll_history", []))
    if not history:
        st.caption("No rolls yet.")
    else:
        for i, entry in enumerate(history):
            st.write(f"{i + 1}. {entry}")
