"""Entrypoint aplikasi web Pixego."""

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.config import NAV_ITEMS
from app.components import render_navigation
from app.theme import inject_css

st.set_page_config(
    page_title="Pixego",
    page_icon=":material/encrypted:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()

pages = [
    st.Page(
        item["file"],
        title=item["label"],
        icon=f":material/{item['icon']}:",
        url_path=item["label"].lower().replace(" ", "-"),
        default=index == 0,
    )
    for index, item in enumerate(NAV_ITEMS)
]
selected_page = st.navigation(pages, position="hidden")
render_navigation(NAV_ITEMS, selected_page.title)
selected_page.run()