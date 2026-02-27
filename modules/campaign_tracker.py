"""Campaign Tracker – manage quests, locations, NPCs, events, and images."""

from __future__ import annotations

import io

import streamlit as st
from db import get_conn

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _campaigns() -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM campaigns ORDER BY name")]


def _create_campaign(name: str, description: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO campaigns (name, description) VALUES (?, ?)", (name, description)
        )
        return cur.lastrowid


def _update_campaign(cid: int, name: str, description: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE campaigns SET name=?, description=? WHERE id=?", (name, description, cid))


def _delete_campaign(cid: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM campaigns WHERE id=?", (cid,))


# -- Quests --
def _quests(cid: int) -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM quests WHERE campaign_id=? ORDER BY created_at DESC", (cid,)
        )]


def _upsert_quest(cid: int, title: str, description: str, status: str, qid: int | None = None) -> None:
    with get_conn() as conn:
        if qid:
            conn.execute(
                "UPDATE quests SET title=?, description=?, status=?, updated_at=datetime('now') WHERE id=?",
                (title, description, status, qid),
            )
        else:
            conn.execute(
                "INSERT INTO quests (campaign_id, title, description, status) VALUES (?,?,?,?)",
                (cid, title, description, status),
            )


def _delete_quest(qid: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM quests WHERE id=?", (qid,))


# -- Locations --
def _locations(cid: int) -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM locations WHERE campaign_id=?", (cid,)
        )]


def _upsert_location(cid: int, name: str, description: str, notes: str, lid: int | None = None) -> None:
    with get_conn() as conn:
        if lid:
            conn.execute(
                "UPDATE locations SET name=?, description=?, notes=? WHERE id=?",
                (name, description, notes, lid),
            )
        else:
            conn.execute(
                "INSERT INTO locations (campaign_id, name, description, notes) VALUES (?,?,?,?)",
                (cid, name, description, notes),
            )


def _delete_location(lid: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM locations WHERE id=?", (lid,))


# -- NPCs --
def _npcs(cid: int) -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM npcs WHERE campaign_id=?", (cid,)
        )]


def _upsert_npc(cid: int, name: str, description: str, relationship: str, notes: str,
                nid: int | None = None) -> None:
    with get_conn() as conn:
        if nid:
            conn.execute(
                "UPDATE npcs SET name=?, description=?, relationship=?, notes=? WHERE id=?",
                (name, description, relationship, notes, nid),
            )
        else:
            conn.execute(
                "INSERT INTO npcs (campaign_id, name, description, relationship, notes) VALUES (?,?,?,?,?)",
                (cid, name, description, relationship, notes),
            )


def _delete_npc(nid: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM npcs WHERE id=?", (nid,))


# -- Events --
def _events(cid: int) -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM events WHERE campaign_id=? ORDER BY created_at DESC", (cid,)
        )]


def _upsert_event(cid: int, title: str, description: str, date_in_game: str,
                  eid: int | None = None) -> None:
    with get_conn() as conn:
        if eid:
            conn.execute(
                "UPDATE events SET title=?, description=?, date_in_game=? WHERE id=?",
                (title, description, date_in_game, eid),
            )
        else:
            conn.execute(
                "INSERT INTO events (campaign_id, title, description, date_in_game) VALUES (?,?,?,?)",
                (cid, title, description, date_in_game),
            )


def _delete_event(eid: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM events WHERE id=?", (eid,))


# -- Images --
def _images(cid: int) -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id, name, created_at FROM campaign_images WHERE campaign_id=?", (cid,)
        )]


def _get_image_data(img_id: int) -> bytes | None:
    with get_conn() as conn:
        row = conn.execute("SELECT data FROM campaign_images WHERE id=?", (img_id,)).fetchone()
    return row["data"] if row else None


def _add_image(cid: int, name: str, data: bytes) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO campaign_images (campaign_id, name, data) VALUES (?,?,?)",
            (cid, name, data),
        )


def _delete_image(img_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM campaign_images WHERE id=?", (img_id,))


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def _quest_status_badge(status: str) -> str:
    return {"active": "🟡", "completed": "✅", "failed": "❌"}.get(status, "•")


def _render_campaigns_panel() -> int | None:
    """Returns the selected campaign ID (or None)."""
    campaigns = _campaigns()

    with st.sidebar:
        st.subheader("📖 Campaigns")
        if not campaigns:
            st.caption("No campaigns yet.")
        else:
            cid = st.selectbox(
                "Active Campaign",
                [c["id"] for c in campaigns],
                format_func=lambda x: next((c["name"] for c in campaigns if c["id"] == x), str(x)),
                key="ct_active_campaign",
            )
            return cid

        with st.form("ct_new_campaign"):
            nc_name = st.text_input("New campaign name")
            nc_desc = st.text_area("Description", height=60)
            if st.form_submit_button("➕ Create"):
                if nc_name:
                    _create_campaign(nc_name, nc_desc)
                    st.rerun()
        return None


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_campaign_tracker() -> None:
    st.header("🗺️ Campaign Tracker")

    campaigns = _campaigns()
    if not campaigns:
        st.info("No campaigns yet.")
        with st.form("ct_create_first"):
            name = st.text_input("Campaign name *")
            desc = st.text_area("Description")
            if st.form_submit_button("➕ Create Campaign"):
                if name:
                    _create_campaign(name, desc)
                    st.rerun()
        return

    # Campaign selector + management
    csel_col, cact_col = st.columns([3, 1])
    sel_cid = csel_col.selectbox(
        "Campaign",
        [c["id"] for c in campaigns],
        format_func=lambda x: next((c["name"] for c in campaigns if c["id"] == x), str(x)),
        key="ct_sel_campaign",
    )

    with cact_col:
        if st.button("➕ New Campaign", key="ct_new_camp"):
            st.session_state["ct_show_new_camp"] = True

    if st.session_state.get("ct_show_new_camp"):
        with st.form("ct_new_camp_form"):
            nc1, nc2 = st.columns(2)
            nc_name = nc1.text_input("Name *")
            nc_desc = nc2.text_area("Description", height=60)
            sf1, sf2 = st.columns(2)
            if sf1.form_submit_button("Create"):
                if nc_name:
                    _create_campaign(nc_name, nc_desc)
                    st.session_state["ct_show_new_camp"] = False
                    st.rerun()
            if sf2.form_submit_button("Cancel"):
                st.session_state["ct_show_new_camp"] = False
                st.rerun()

    # Current campaign info
    cur_camp = next((c for c in campaigns if c["id"] == sel_cid), None)
    if not cur_camp:
        return

    with st.expander(f"📝 Edit Campaign: {cur_camp['name']}", expanded=False):
        with st.form(f"edit_camp_{sel_cid}"):
            e_name = st.text_input("Name", value=cur_camp["name"])
            e_desc = st.text_area("Description", value=cur_camp.get("description", ""))
            ec1, ec2 = st.columns(2)
            if ec1.form_submit_button("💾 Save"):
                _update_campaign(sel_cid, e_name, e_desc)
                st.success("Campaign updated")
                st.rerun()
            if ec2.form_submit_button("🗑️ Delete Campaign"):
                _delete_campaign(sel_cid)
                st.rerun()

    st.divider()

    tab_q, tab_loc, tab_npc, tab_ev, tab_img = st.tabs(
        ["📜 Quests", "📍 Locations", "👥 NPCs", "📅 Events", "🖼️ Images"]
    )

    # ---- Quests ----
    with tab_q:
        with st.expander("➕ Add Quest", expanded=False):
            with st.form("add_quest"):
                qt, qd = st.columns([2, 3])
                q_title = qt.text_input("Title *")
                q_desc = qd.text_area("Description", height=60)
                q_status = st.selectbox("Status", ["active", "completed", "failed"])
                if st.form_submit_button("Add"):
                    if q_title:
                        _upsert_quest(sel_cid, q_title, q_desc, q_status)
                        st.rerun()

        for q in _quests(sel_cid):
            badge = _quest_status_badge(q["status"])
            with st.expander(f"{badge} {q['title']} [{q['status']}]"):
                with st.form(f"edit_q_{q['id']}"):
                    eq_t = st.text_input("Title", value=q["title"])
                    eq_d = st.text_area("Description", value=q.get("description", ""))
                    eq_s = st.selectbox("Status", ["active", "completed", "failed"],
                                        index=["active", "completed", "failed"].index(q["status"]))
                    qc1, qc2 = st.columns(2)
                    if qc1.form_submit_button("💾 Save"):
                        _upsert_quest(sel_cid, eq_t, eq_d, eq_s, qid=q["id"])
                        st.rerun()
                    if qc2.form_submit_button("🗑️ Delete"):
                        _delete_quest(q["id"])
                        st.rerun()

    # ---- Locations ----
    with tab_loc:
        with st.expander("➕ Add Location", expanded=False):
            with st.form("add_loc"):
                l_name = st.text_input("Name *")
                l_desc = st.text_area("Description", height=60)
                l_notes = st.text_area("Notes", height=40)
                if st.form_submit_button("Add"):
                    if l_name:
                        _upsert_location(sel_cid, l_name, l_desc, l_notes)
                        st.rerun()

        for loc in _locations(sel_cid):
            with st.expander(f"📍 {loc['name']}"):
                with st.form(f"edit_loc_{loc['id']}"):
                    el_n = st.text_input("Name", value=loc["name"])
                    el_d = st.text_area("Description", value=loc.get("description", ""))
                    el_no = st.text_area("Notes", value=loc.get("notes", ""))
                    lc1, lc2 = st.columns(2)
                    if lc1.form_submit_button("💾 Save"):
                        _upsert_location(sel_cid, el_n, el_d, el_no, lid=loc["id"])
                        st.rerun()
                    if lc2.form_submit_button("🗑️ Delete"):
                        _delete_location(loc["id"])
                        st.rerun()

    # ---- NPCs ----
    with tab_npc:
        with st.expander("➕ Add NPC", expanded=False):
            with st.form("add_npc"):
                n_name = st.text_input("Name *")
                n_rel, n_desc = st.columns(2)
                n_relationship = n_rel.text_input("Relationship")
                n_description = n_desc.text_area("Description", height=60)
                n_notes = st.text_area("Notes", height=40)
                if st.form_submit_button("Add"):
                    if n_name:
                        _upsert_npc(sel_cid, n_name, n_description, n_relationship, n_notes)
                        st.rerun()

        for npc in _npcs(sel_cid):
            with st.expander(f"👤 {npc['name']} [{npc.get('relationship', '')}]"):
                with st.form(f"edit_npc_{npc['id']}"):
                    en_n = st.text_input("Name", value=npc["name"])
                    en_r = st.text_input("Relationship", value=npc.get("relationship", ""))
                    en_d = st.text_area("Description", value=npc.get("description", ""))
                    en_no = st.text_area("Notes", value=npc.get("notes", ""))
                    nc1, nc2 = st.columns(2)
                    if nc1.form_submit_button("💾 Save"):
                        _upsert_npc(sel_cid, en_n, en_d, en_r, en_no, nid=npc["id"])
                        st.rerun()
                    if nc2.form_submit_button("🗑️ Delete"):
                        _delete_npc(npc["id"])
                        st.rerun()

    # ---- Events ----
    with tab_ev:
        with st.expander("➕ Add Event / Session Note", expanded=False):
            with st.form("add_event"):
                ev_t = st.text_input("Title *")
                ev_date, ev_desc = st.columns(2)
                ev_d = ev_date.text_input("In-game date")
                ev_de = ev_desc.text_area("Description", height=80)
                if st.form_submit_button("Add"):
                    if ev_t:
                        _upsert_event(sel_cid, ev_t, ev_de, ev_d)
                        st.rerun()

        for ev in _events(sel_cid):
            with st.expander(f"📅 {ev['title']} {('— ' + ev['date_in_game']) if ev.get('date_in_game') else ''}"):
                with st.form(f"edit_ev_{ev['id']}"):
                    ee_t = st.text_input("Title", value=ev["title"])
                    ee_d = st.text_input("In-game date", value=ev.get("date_in_game", ""))
                    ee_de = st.text_area("Description", value=ev.get("description", ""))
                    ec1, ec2 = st.columns(2)
                    if ec1.form_submit_button("💾 Save"):
                        _upsert_event(sel_cid, ee_t, ee_de, ee_d, eid=ev["id"])
                        st.rerun()
                    if ec2.form_submit_button("🗑️ Delete"):
                        _delete_event(ev["id"])
                        st.rerun()

    # ---- Images ----
    with tab_img:
        st.write("Upload maps, handouts, or any campaign images.")
        uploaded = st.file_uploader(
            "Upload image", type=["png", "jpg", "jpeg", "gif", "webp"], key="ct_img_upload"
        )
        if uploaded:
            img_name = st.text_input("Image name", value=uploaded.name, key="ct_img_name")
            if st.button("💾 Save Image", key="ct_img_save"):
                _add_image(sel_cid, img_name, uploaded.getvalue())
                st.success(f"Saved {img_name}")
                st.rerun()

        images = _images(sel_cid)
        if not images:
            st.caption("No images uploaded yet.")
        else:
            cols = st.columns(3)
            for i, img in enumerate(images):
                data = _get_image_data(img["id"])
                if data:
                    with cols[i % 3]:
                        st.image(data, caption=img["name"], use_container_width=True)
                        if st.button("🗑️ Delete", key=f"del_img_{img['id']}"):
                            _delete_image(img["id"])
                            st.rerun()
