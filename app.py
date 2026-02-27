"""D&D Helper – main Streamlit application entry point."""

import streamlit as st

from db import init_db

st.set_page_config(
    page_title="D&D Helper",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialise the database on every run (idempotent – CREATE IF NOT EXISTS)
init_db()

# ---------------------------------------------------------------------------
# Gemini API key management (sidebar)
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🎲 D&D Helper")
    st.divider()

    # Gemini API key
    with st.expander("🔑 Gemini API Key", expanded=False):
        from utils.gemini import init_gemini, is_initialised

        if is_initialised():
            st.success("Gemini API connected ✅")
            if st.button("Disconnect", key="gemini_disconnect"):
                import utils.gemini as _gm
                _gm._client = None
                st.rerun()
        else:
            key_input = st.text_input(
                "Enter API key", type="password", key="gemini_key_input",
                placeholder="AIza…"
            )
            if st.button("Connect", key="gemini_connect"):
                if key_input:
                    try:
                        init_gemini(key_input)
                        st.success("Connected!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")
                else:
                    st.warning("Please enter an API key.")

    st.divider()

    PAGES = {
        "🧙 Characters":     "Characters",
        "🎲 Dice Roller":    "Dice Roller",
        "⚔️ Encounter Builder": "Encounter Builder",
        "🗺️ Campaign Tracker":  "Campaign Tracker",
        "📚 Creature / Spell / Item Database": "Database",
        "⚙️ Settings": "Settings",
    }

    # Apply any pending navigation request before the radio widget is instantiated
    if "pending_nav" in st.session_state:
        st.session_state["nav_page"] = st.session_state.pop("pending_nav")

    page = st.radio("Navigation", list(PAGES.keys()), key="nav_page", label_visibility="collapsed")
    selected = PAGES[page]

# ---------------------------------------------------------------------------
# Page routing
# ---------------------------------------------------------------------------

if selected == "Characters":
    from modules.character_sheet import render_character_sheet
    render_character_sheet()

elif selected == "Dice Roller":
    from modules.dice_roller import render_dice_roller
    render_dice_roller()

elif selected == "Encounter Builder":
    from modules.encounter_builder import render_encounter_builder
    render_encounter_builder()

elif selected == "Campaign Tracker":
    from modules.campaign_tracker import render_campaign_tracker
    render_campaign_tracker()

elif selected == "Database":
    from modules.creature_database import render_creature_database
    render_creature_database()

elif selected == "Settings":
    from utils.export import render_data_management
    render_data_management()
