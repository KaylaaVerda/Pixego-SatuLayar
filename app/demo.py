"""Perhitungan contoh Beranda dari gambar tetap di sample_images/."""

from __future__ import annotations

import io
from pathlib import Path

import streamlit as st
from PIL import Image

import stego_core as core
from app.services import embed_message, image_to_png_bytes


@st.cache_data(show_spinner=False)
def home_demo() -> dict:
    root = Path(__file__).resolve().parents[1]
    cover_path = root / "sample_images" / "cover_tekstur.png"
    cover = core.load_cover(cover_path, max_side=512)
    message = "Contoh pesan Pixego untuk pengukuran gambar dan chi-square."
    random_stego, random_info = embed_message(cover, message, "pixego-demo-password", "random", 1)
    sequential_stego, _ = embed_message(cover, message, "pixego-demo-password", "sequential", 1)
    x_random, y_random = core.chi_square_progressive(random_stego, steps=10)
    x_sequential, y_sequential = core.chi_square_progressive(sequential_stego, steps=10)
    return {
        "cover_png": image_to_png_bytes(cover),
        "stego_png": image_to_png_bytes(random_stego),
        "mse": core.mse(cover, random_stego),
        "psnr": core.psnr(cover, random_stego),
        "capacity": random_info["kapasitas_byte"],
        "x": x_random.tolist(),
        "random_p": y_random.tolist(),
        "sequential_x": x_sequential.tolist(),
        "sequential_p": y_sequential.tolist(),
    }