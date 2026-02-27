"""Export the full database to a ZIP archive and restore from one."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime

from db import get_conn

_TABLES = [
    "campaigns",
    "characters",
    "quests",
    "locations",
    "npcs",
    "events",
    "creatures",
    "spells",
    "items",
]

# campaign_images exported separately due to BLOB data
_BLOB_TABLE = "campaign_images"


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_to_zip() -> bytes:
    """Dump every table to JSON and bundle into a ZIP archive (bytes)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    buf = io.BytesIO()

    with get_conn() as conn, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for table in _TABLES:
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]
            zf.writestr(f"{table}.json", json.dumps(rows, indent=2, ensure_ascii=False))

        # Export images as base64
        import base64
        rows = []
        for r in conn.execute(f"SELECT * FROM {_BLOB_TABLE}"):
            d = dict(r)
            if d.get("data"):
                d["data"] = base64.b64encode(d["data"]).decode()
            rows.append(d)
        zf.writestr(f"{_BLOB_TABLE}.json", json.dumps(rows, indent=2))

        # Write a manifest
        zf.writestr("manifest.json", json.dumps({"exported_at": ts, "tables": _TABLES + [_BLOB_TABLE]}))

    return buf.getvalue()


def get_export_filename() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"dnd_helper_export_{ts}.zip"


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------

_UPSERT_SQL: dict[str, str] = {}  # populated lazily


def _get_columns(conn, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [r["name"] for r in rows]


def restore_from_zip(data: bytes) -> dict[str, int]:
    """Restore records from a ZIP archive.

    Returns a dict mapping table name -> number of rows upserted.
    """
    import base64

    results: dict[str, int] = {}

    with get_conn() as conn, zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()

        for table in _TABLES + [_BLOB_TABLE]:
            fname = f"{table}.json"
            if fname not in names:
                continue

            rows = json.loads(zf.read(fname))
            if not rows:
                results[table] = 0
                continue

            cols = _get_columns(conn, table)
            # Only keep columns that exist in the current schema
            valid_rows = [{k: v for k, v in r.items() if k in cols} for r in rows]

            if table == _BLOB_TABLE:
                for r in valid_rows:
                    if r.get("data"):
                        r["data"] = base64.b64decode(r["data"])

            if not valid_rows:
                results[table] = 0
                continue

            all_cols = list(valid_rows[0].keys())
            placeholders = ", ".join(f":{c}" for c in all_cols)
            col_list = ", ".join(all_cols)
            update_set = ", ".join(f"{c}=excluded.{c}" for c in all_cols if c != "id")

            sql = (
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
                f"ON CONFLICT(id) DO UPDATE SET {update_set}"
            )
            conn.executemany(sql, valid_rows)
            results[table] = len(valid_rows)

    return results


# ---------------------------------------------------------------------------
# Streamlit UI helper (imported by app.py)
# ---------------------------------------------------------------------------

def render_data_management() -> None:
    import streamlit as st

    st.header("⚙️ Settings & Data Management")

    # ---- Export ----
    st.subheader("Export Database")
    st.write("Download all data as a timestamped ZIP archive.")
    if st.button("📦 Generate Export", key="gen_export"):
        with st.spinner("Exporting…"):
            zdata = export_to_zip()
        st.download_button(
            label="⬇️ Download ZIP",
            data=zdata,
            file_name=get_export_filename(),
            mime="application/zip",
            key="dl_export",
        )

    st.divider()

    # ---- Restore ----
    st.subheader("Restore from Archive")
    st.warning(
        "Restoring will **upsert** records from the archive into the current database. "
        "Existing records with matching IDs will be **overwritten**.",
        icon="⚠️",
    )
    uploaded = st.file_uploader("Upload a .zip export file", type=["zip"], key="restore_upload")
    if uploaded:
        st.info(f"File: **{uploaded.name}** ({len(uploaded.getvalue()):,} bytes)")
        if st.button("🔄 Restore Now", key="do_restore"):
            try:
                results = restore_from_zip(uploaded.getvalue())
                st.success("Restore complete!")
                for table, count in results.items():
                    st.write(f"  • `{table}`: {count} rows upserted")
            except Exception as e:
                st.error(f"Restore failed: {e}")
