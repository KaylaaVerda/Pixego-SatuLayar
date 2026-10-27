"""Entrypoint aplikasi web Pixego — satu halaman tanpa scroll."""

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.theme import inject_css, inject_onepage_css
from app.onepage import render_onepage

st.set_page_config(
    page_title="Pixego — Steganografi & Kriptografi Citra",
    page_icon=":material/encrypted:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()
inject_onepage_css()
render_onepage()