"""
app/onepage.py
Satu halaman utama Pixego — tanpa scroll, semua elemen dalam 100vh.

Layout:
  render_onepage()
    ├── render_header()     -- logo, 4 info field, popover Tentang
    ├── render_toolbar()    -- 7 tombol sama lebar
    ├── render_row1()       -- Buka Gambar | Enkripsi | Uji Kunci & Analisis
    ├── render_row2()       -- Histogram Asli | Histogram Stego | Evaluasi Metrik
    ├── render_row3()       -- Uji Kunci Salah | Perbandingan Lapisan | Metode Pengujian
    └── render_footer()     -- 1 baris kecil teks footer

Teknik Streamlit yang dipakai:
  - st.container(key="card_xxx", border=True) untuk setiap panel kartu
  - CSS .st-key-card_xxx untuk styling kartu via theme.py
  - TIDAK membuka <div> di satu st.markdown dan menutupnya di st.markdown lain
  - st.tabs hanya di dalam kartu "METODE PENGUJIAN" (row3_metode)
  - on_click callback di toolbar untuk operasi berat (tidak di body)
"""

from __future__ import annotations

import io
import math
import os
import time

import numpy as np
import pandas as pd
from PIL import Image
import streamlit as st

import stego_core as core
from app.config import DEVELOPER, FOOTER_TEXT
from app.services import (
    capacity_bytes,
    clear_session_data,
    embed_message,
    extract_message,
    image_to_png_bytes,
    load_cover_upload,
    load_stego_upload,
)
import metrics as met


# ============================================================
# Helper: Baca gambar dari session_state bytes
# ============================================================

def _img_from_session(key: str) -> Image.Image | None:
    """Kembalikan PIL Image dari bytes di session_state, atau None."""
    data = st.session_state.get(key)
    if data:
        try:
            return Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            pass
    return None


def _fmt(val, fmt=".4f", fallback="—") -> str:
    """Format angka float, tangani None/inf/nan dengan graceful."""
    if val is None:
        return fallback
    try:
        if math.isinf(val):
            return "∞"
        if math.isnan(val):
            return "?"
        return format(val, fmt)
    except (TypeError, ValueError):
        return fallback


# ============================================================
# Callback toolbar — dipanggil lewat on_click agar aman
# ============================================================

def _cb_enkripsi() -> None:
    """Callback tombol ENKRIPSI: baca session_state, jalankan embed."""
    cover = _img_from_session("pixego_cover_png")
    # Jika belum ada cover_png, coba dari uploader
    if cover is None:
        up = st.session_state.get("pixego_cover_upload")
        if up is not None:
            try:
                cover, _ = load_cover_upload(up)
                st.session_state["pixego_cover_png"] = image_to_png_bytes(cover)
            except Exception:
                st.session_state["pixego_embed_error"] = "Gagal memuat gambar cover."
                return

    if cover is None:
        st.session_state["pixego_embed_error"] = "Unggah gambar cover terlebih dahulu."
        return

    message = st.session_state.get("pixego_message", "")
    password = st.session_state.get("pixego_embed_password", "")
    mode_label = st.session_state.get("pixego_embed_mode", "Acak berbasis kunci")
    mode = "random" if "Acak" in mode_label else "sequential"
    bits = st.session_state.get("pixego_embed_bits", 1)

    if not password:
        st.session_state["pixego_embed_error"] = "Password tidak boleh kosong."
        return
    if not message:
        st.session_state["pixego_embed_error"] = "Pesan tidak boleh kosong."
        return

    try:
        t0 = time.perf_counter()
        stego, info = embed_message(cover, message, password, mode, bits)
        elapsed_embed = time.perf_counter() - t0

        st.session_state["pixego_stego_png"] = image_to_png_bytes(stego)
        st.session_state["pixego_last_info"] = info
        st.session_state["pixego_result_ready"] = True
        st.session_state.pop("pixego_embed_error", None)

        # Hitung dan simpan metrik — tidak dihitung ulang di tiap rerun
        _simpan_metrik(cover, stego, elapsed_embed=elapsed_embed)
    except core.StegoError as e:
        st.session_state["pixego_embed_error"] = str(e)
        st.session_state.pop("pixego_result_ready", None)
    except Exception:
        st.session_state["pixego_embed_error"] = "Proses gagal. Periksa input."
        st.session_state.pop("pixego_result_ready", None)


def _cb_dekripsi() -> None:
    """Callback tombol DEKRIPSI: baca session_state, jalankan extract."""
    # Prioritas: uploader stego, lalu stego dari sesi
    stego = None
    up = st.session_state.get("pixego_stego_upload")
    if up is not None:
        try:
            stego = load_stego_upload(up, getattr(up, "name", ""))
        except core.StegoError as e:
            st.session_state["pixego_extract_error"] = str(e)
            return
    if stego is None:
        stego = _img_from_session("pixego_stego_png")
    if stego is None:
        st.session_state["pixego_extract_error"] = "Tidak ada gambar stego. Enkripsi dulu atau unggah stego."
        return

    password = st.session_state.get("pixego_extract_password", "")
    if not password:
        st.session_state["pixego_extract_error"] = "Password ekstraksi tidak boleh kosong."
        return

    try:
        t0 = time.perf_counter()
        raw = extract_message(stego, password)
        elapsed_extract = time.perf_counter() - t0

        # Simpan waktu ekstrak ke metrik yang sudah ada
        m = st.session_state.get("pixego_metrics", {})
        m["Waktu Ekstrak (ms)"] = elapsed_extract * 1000
        st.session_state["pixego_metrics"] = m

        try:
            text = raw.decode("utf-8")
            st.session_state["pixego_extracted_text"] = text
        except UnicodeDecodeError:
            st.session_state["pixego_extracted_text"] = f"[Data biner, {len(raw)} byte]"

        st.session_state.pop("pixego_extract_error", None)
    except core.StegoError as e:
        st.session_state["pixego_extract_error"] = str(e)
        st.session_state.pop("pixego_extracted_text", None)
    except Exception:
        st.session_state["pixego_extract_error"] = "Ekstraksi gagal."
        st.session_state.pop("pixego_extracted_text", None)


def _cb_analisis() -> None:
    """Callback tombol ANALISIS: hitung semua metrik dan simpan ke session."""
    cover = _img_from_session("pixego_cover_png")
    stego = _img_from_session("pixego_stego_png")
    if cover is None or stego is None:
        st.session_state["pixego_analisis_error"] = "Enkripsi gambar terlebih dahulu."
        return
    try:
        _simpan_metrik(cover, stego, elapsed_embed=None)
        st.session_state.pop("pixego_analisis_error", None)
    except Exception as e:
        st.session_state["pixego_analisis_error"] = f"Analisis gagal: {e}"


def _cb_uji_kunci() -> None:
    """Callback tombol UJI KUNCI: set flag agar bagian row3 menjalankan uji."""
    st.session_state["pixego_run_uji_kunci"] = True


def _cb_reset() -> None:
    """Callback tombol RESET: hapus semua data sesi."""
    clear_session_data(st.session_state)
    for extra in ("pixego_embed_error", "pixego_extract_error", "pixego_analisis_error",
                  "pixego_extracted_text", "pixego_metrics", "pixego_histograms",
                  "pixego_run_uji_kunci", "pixego_uji_kunci_result",
                  "pixego_compare_result"):
        st.session_state.pop(extra, None)


def _cb_buka_gambar() -> None:
    """Callback tombol BUKA GAMBAR — uploader ada di panel, tombol hanya menginformasikan."""
    st.toast("Pilih gambar di panel BUKA GAMBAR (kolom kiri atas).", icon="📁")


# ============================================================
# Helper: Simpan metrik ke session_state
# ============================================================

def _simpan_metrik(cover: Image.Image, stego: Image.Image, elapsed_embed: float | None) -> None:
    """Hitung semua metrik dan simpan ke st.session_state["pixego_metrics"]."""
    info = st.session_state.get("pixego_last_info", {})

    mse_val = core.mse(cover, stego)
    psnr_val = core.psnr(cover, stego)
    ssim_val = met.ssim(cover, stego)
    ent_cover = met.entropy(cover)
    ent_stego = met.entropy(stego)
    npcr_val = met.npcr(cover, stego)
    uaci_val = met.uaci(cover, stego)
    chi_cover = core.chi_square_full(cover)
    chi_stego = core.chi_square_full(stego)
    corr_cover = met.adjacent_correlation(cover)
    corr_stego = met.adjacent_correlation(stego)

    # Throughput berdasarkan waktu embed (jika tersedia)
    tp = None
    if elapsed_embed and info.get("pesan_byte"):
        tp = met.throughput_kbps(info["pesan_byte"], elapsed_embed)

    # Pertahankan waktu ekstrak jika sudah ada
    m_old = st.session_state.get("pixego_metrics", {})
    elapsed_extract = m_old.get("Waktu Ekstrak (ms)", None)

    st.session_state["pixego_metrics"] = {
        "Entropi Cover": ent_cover,
        "Entropi Stego": ent_stego,
        "Chi-square Cover (p)": chi_cover,
        "Chi-square Stego (p)": chi_stego,
        "Korelasi H Cover": corr_cover["H"],
        "Korelasi H Stego": corr_stego["H"],
        "Korelasi V Cover": corr_cover["V"],
        "Korelasi V Stego": corr_stego["V"],
        "Korelasi D Cover": corr_cover["D"],
        "Korelasi D Stego": corr_stego["D"],
        "MSE": mse_val,
        "PSNR (dB)": psnr_val,
        "SSIM": ssim_val,
        "NPCR (%)": npcr_val,
        "UACI (%)": uaci_val,
        "Waktu Embed (ms)": (elapsed_embed * 1000) if elapsed_embed else m_old.get("Waktu Embed (ms)"),
        "Waktu Ekstrak (ms)": elapsed_extract,
        "Throughput (KB/s)": tp,
        "Kapasitas Terpakai (%)": info.get("penggunaan_kapasitas_%"),
    }

    # Histogram untuk Baris 2
    arr_cover = np.array(cover.convert("RGB"))
    arr_stego = np.array(stego.convert("RGB"))
    hist_c, hist_s = {}, {}
    for ch, name in enumerate(["R", "G", "B"]):
        vc, _ = np.histogram(arr_cover[:, :, ch], bins=64, range=(0, 256))
        vs, _ = np.histogram(arr_stego[:, :, ch], bins=64, range=(0, 256))
        hist_c[name] = vc
        hist_s[name] = vs
    st.session_state["pixego_histograms"] = {"cover": hist_c, "stego": hist_s}


# ============================================================
# HEADER
# ============================================================

def render_header() -> None:
    """Header satu baris: logo kiri, info field tengah, popover Tentang kanan."""
    from app.components import icon_svg

    bits = st.session_state.get("pixego_embed_bits", 1)

    col_logo, col_fields, col_about = st.columns([2, 7, 1], gap="small",
                                                  vertical_alignment="center")

    with col_logo:
        st.markdown(
            f'<div class="op-logo">'
            f'{icon_svg("shield", 18)}'
            f'<div>'
            f'<div>Pixego</div>'
            f'<div class="op-logo-sub">Steganografi &amp; Kriptografi Citra</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_fields:
        fc1, fc2, fc3, fc4 = st.columns(4, gap="small")
        with fc1:
            st.markdown(
                '<div class="op-info-field">'
                '<span class="op-info-label">Algoritma</span>'
                '<span class="op-info-value">AES-256-GCM</span>'
                '</div>', unsafe_allow_html=True)
        with fc2:
            st.markdown(
                '<div class="op-info-field">'
                '<span class="op-info-label">Kunci</span>'
                '<span class="op-info-value">Argon2id + HKDF</span>'
                '</div>', unsafe_allow_html=True)
        with fc3:
            st.markdown(
                '<div class="op-info-field">'
                '<span class="op-info-label">Metode</span>'
                '<span class="op-info-value">LSB + Analisis</span>'
                '</div>', unsafe_allow_html=True)
        with fc4:
            # Bit per kanal — fungsional, key pixego_embed_bits
            st.select_slider(
                "Bit/kanal",
                options=[1, 2, 3],
                key="pixego_embed_bits",
                label_visibility="visible",
            )

    with col_about:
        with st.popover("Tentang", use_container_width=True):
            for k, v in DEVELOPER.items():
                st.markdown(
                    f'<div style="font-size:.72rem;margin-bottom:.2rem;">'
                    f'<span style="color:var(--muted);font-size:.6rem;text-transform:uppercase;'
                    f'letter-spacing:.05em;">{k}</span><br>'
                    f'<strong style="color:var(--ink)">{v}</strong>'
                    f'</div>',
                    unsafe_allow_html=True)


# ============================================================
# TOOLBAR
# ============================================================

def render_toolbar() -> None:
    """Toolbar 7 tombol sama lebar menggunakan st.columns."""
    stego_ready = bool(st.session_state.get("pixego_stego_png"))

    t1, t2, t3, t4, t5, t6, t7 = st.columns(7, gap="small")

    with t1:
        st.button("📁 Buka Gambar", key="tb_buka", use_container_width=True,
                  on_click=_cb_buka_gambar)
    with t2:
        st.button("🔒 Enkripsi", key="tb_enkripsi", use_container_width=True,
                  type="primary", on_click=_cb_enkripsi)
    with t3:
        st.button("🔓 Dekripsi", key="tb_dekripsi", use_container_width=True,
                  type="primary", on_click=_cb_dekripsi)
    with t4:
        st.button("🔑 Uji Kunci", key="tb_uji_kunci", use_container_width=True,
                  on_click=_cb_uji_kunci)
    with t5:
        st.button("📊 Analisis", key="tb_analisis", use_container_width=True,
                  on_click=_cb_analisis)
    with t6:
        st.button("🗑 Reset", key="tb_reset", use_container_width=True,
                  on_click=_cb_reset)
    with t7:
        # SIMPAN CITRA: download button, nonaktif jika belum ada stego
        if stego_ready:
            stego_bytes = st.session_state.get("pixego_stego_png", b"")
            st.download_button(
                "💾 Simpan Citra", data=stego_bytes,
                file_name="stego.png", mime="image/png",
                key="tb_simpan", use_container_width=True,
            )
        else:
            st.button("💾 Simpan Citra", key="tb_simpan_dis",
                      use_container_width=True, disabled=True)


# ============================================================
# BARIS 1 — Kolom 1: BUKA GAMBAR
# ============================================================

def _render_buka_gambar() -> None:
    """Panel kiri baris 1: uploader cover + preview + info kapasitas."""
    with st.container(key="card_row1_buka", border=True):
        st.markdown('<div class="card-title">📁 Buka Gambar</div>', unsafe_allow_html=True)

        cover_file = st.file_uploader(
            "Pilih gambar cover",
            type=["png", "jpg", "jpeg", "bmp", "webp"],
            key="pixego_cover_upload",
            label_visibility="collapsed",
        )

        cover = None
        if cover_file is not None:
            try:
                cover, resized = load_cover_upload(cover_file)
                # Simpan ke session sebagai PNG bytes
                cover_bytes = image_to_png_bytes(cover)
                if st.session_state.get("pixego_cover_png") != cover_bytes:
                    st.session_state["pixego_cover_png"] = cover_bytes
                if resized:
                    st.caption("Diperkecil otomatis (sisi maks 1024px)")
            except core.StegoError as e:
                st.error(str(e), icon="⚠️")
            except Exception:
                st.error("Gambar tidak dapat diproses.", icon="⚠️")
        else:
            # Tampilkan dari session jika sudah ada
            cover = _img_from_session("pixego_cover_png")

        if cover is not None:
            st.image(cover, caption=None, use_container_width=True)
            bits = st.session_state.get("pixego_embed_bits", 1)
            cap = capacity_bytes(cover.size, bits)
            st.caption(f"🖼 {cover.width}×{cover.height}  ·  kapasitas {cap:,} byte ({bits} bit/kanal)")


# ============================================================
# BARIS 1 — Kolom 2: ENKRIPSI
# ============================================================

def _render_enkripsi() -> None:
    """Panel tengah baris 1: textarea pesan, password, mode, progress, tombol, preview stego."""
    with st.container(key="card_row1_enkripsi", border=True):
        st.markdown('<div class="card-title">🔒 Enkripsi</div>', unsafe_allow_html=True)

        st.text_area(
            "Pesan rahasia",
            placeholder="Tulis pesan yang ingin disembunyikan…",
            key="pixego_message",
            height=68,
            label_visibility="collapsed",
        )
        st.text_input(
            "Password enkripsi",
            type="password",
            key="pixego_embed_password",
            placeholder="Password enkripsi…",
            label_visibility="collapsed",
        )
        st.radio(
            "Mode penyisipan",
            ["Acak berbasis kunci", "Sekuensial"],
            horizontal=True,
            key="pixego_embed_mode",
            label_visibility="collapsed",
        )

        # Progress kapasitas (tanpa menghitung ulang gambar)
        cover = _img_from_session("pixego_cover_png")
        if cover is not None:
            bits = st.session_state.get("pixego_embed_bits", 1)
            cap = capacity_bytes(cover.size, bits)
            msg = st.session_state.get("pixego_message", "")
            msg_bytes = len(msg.encode("utf-8")) if msg else 0
            usage = min(msg_bytes / max(cap, 1), 1.0)
            st.progress(usage, text=f"{msg_bytes}/{cap} byte  ({usage*100:.1f}%)")
        else:
            st.progress(0.0, text="Unggah gambar cover terlebih dahulu")

        # Error enkripsi
        err = st.session_state.get("pixego_embed_error")
        if err:
            st.error(err, icon="⚠️")

        # Preview stego hasil enkripsi
        stego = _img_from_session("pixego_stego_png")
        if stego is not None:
            st.caption("Preview Stego")
            st.image(stego, caption=None, use_container_width=True)


# ============================================================
# BARIS 1 — Kolom 3: UJI KUNCI & DEKRIPSI
# ============================================================

def _render_uji_dan_dekripsi() -> None:
    """Panel kanan baris 1: uploader stego, password ekstrak, tombol, hasil."""
    with st.container(key="card_row1_dekripsi", border=True):
        st.markdown('<div class="card-title">🔓 Uji Kunci &amp; Analisis</div>', unsafe_allow_html=True)

        stego_up = st.file_uploader(
            "Stego PNG/BMP",
            type=["png", "bmp"],
            key="pixego_stego_upload",
            label_visibility="collapsed",
        )
        if stego_up is None:
            stego_sess = _img_from_session("pixego_stego_png")
            if stego_sess is not None:
                st.caption("Menggunakan stego dari sesi enkripsi")

        st.text_input(
            "Password ekstraksi",
            type="password",
            key="pixego_extract_password",
            placeholder="Password ekstraksi…",
            label_visibility="collapsed",
        )

        # Tombol inline (pakai kolom kecil agar tidak memenuhi lebar)
        bc1, bc2 = st.columns([1, 1], gap="small")
        with bc1:
            st.button("🔓 Dekripsi Pesan", key="btn_dekripsi_inline",
                      use_container_width=True, type="primary",
                      on_click=_cb_dekripsi)
        with bc2:
            st.button("📊 Analisis", key="btn_analisis_inline",
                      use_container_width=True, on_click=_cb_analisis)

        # Tampilkan error atau hasil
        err = st.session_state.get("pixego_extract_error")
        if err:
            st.error(err, icon="⚠️")

        hasil = st.session_state.get("pixego_extracted_text")
        if hasil is not None:
            st.text_area("Pesan terdekripsi", value=hasil,
                         key="pixego_result_display", disabled=True,
                         height=60, label_visibility="visible")


# ============================================================
# BARIS 1 — render gabungan
# ============================================================

def render_row1() -> None:
    """Baris 1: tiga kolom berdampingan."""
    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        _render_buka_gambar()
    with c2:
        _render_enkripsi()
    with c3:
        _render_uji_dan_dekripsi()


# ============================================================
# BARIS 2 — Histogram + Evaluasi Metrik
# ============================================================

def _render_histogram(title: str, hist_data: dict | None) -> None:
    """Panel histogram RGB untuk cover atau stego."""
    label = title.lower().replace(" ", "_")
    with st.container(key=f"card_row2_{label}", border=True):
        st.markdown(f'<div class="card-title">{title}</div>', unsafe_allow_html=True)
        if hist_data is None:
            st.caption("Belum ada data — jalankan Enkripsi atau Analisis terlebih dahulu.")
            return
        edges = np.arange(64) * 4  # titik tengah bin
        df = pd.DataFrame({
            "R": hist_data["R"],
            "G": hist_data["G"],
            "B": hist_data["B"],
        }, index=edges)
        df.index.name = "Nilai piksel"
        st.line_chart(df, height=100, use_container_width=True)


def _render_evaluasi_metrik() -> None:
    """Panel evaluasi metrik: tabel padat Cover vs Stego."""
    with st.container(key="card_row2_metrik", border=True):
        st.markdown('<div class="card-title">📋 Evaluasi Metrik</div>', unsafe_allow_html=True)
        m = st.session_state.get("pixego_metrics")
        if m is None:
            st.caption("Belum ada data — jalankan Enkripsi atau Analisis.")
            return

        rows = [
            ("Entropi", _fmt(m.get("Entropi Cover"), ".4f"), _fmt(m.get("Entropi Stego"), ".4f")),
            ("Chi-square (p)", _fmt(m.get("Chi-square Cover (p)"), ".4f"), _fmt(m.get("Chi-square Stego (p)"), ".4f")),
            ("Korelasi H", _fmt(m.get("Korelasi H Cover"), ".4f"), _fmt(m.get("Korelasi H Stego"), ".4f")),
            ("Korelasi V", _fmt(m.get("Korelasi V Cover"), ".4f"), _fmt(m.get("Korelasi V Stego"), ".4f")),
            ("Korelasi D", _fmt(m.get("Korelasi D Cover"), ".4f"), _fmt(m.get("Korelasi D Stego"), ".4f")),
            ("MSE", _fmt(m.get("MSE"), ".4f"), "—"),
            ("PSNR (dB)", _fmt(m.get("PSNR (dB)"), ".2f"), "—"),
            ("SSIM", _fmt(m.get("SSIM"), ".4f"), "—"),
            ("NPCR (%)", _fmt(m.get("NPCR (%)"), ".2f"), "—"),
            ("UACI (%)", _fmt(m.get("UACI (%)"), ".2f"), "—"),
            ("Waktu Embed (ms)", _fmt(m.get("Waktu Embed (ms)"), ".1f"), "—"),
            ("Waktu Ekstrak (ms)", _fmt(m.get("Waktu Ekstrak (ms)"), ".1f"), "—"),
            ("Throughput (KB/s)", _fmt(m.get("Throughput (KB/s)"), ".2f"), "—"),
            ("Kapasitas (%)  ", _fmt(m.get("Kapasitas Terpakai (%)"), ".2f"), "—"),
        ]

        # Buat tabel HTML — tidak perlu library baru
        rows_html = "".join(
            f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td></tr>"
            for r in rows
        )
        table_html = (
            '<table class="metrics-table">'
            '<thead><tr><th>Metrik</th><th>Cover</th><th>Stego</th></tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            '</table>'
        )
        st.markdown(table_html, unsafe_allow_html=True)


def render_row2() -> None:
    """Baris 2: Histogram cover | Histogram stego | Tabel metrik."""
    hists = st.session_state.get("pixego_histograms")
    cover_hist = hists["cover"] if hists else None
    stego_hist = hists["stego"] if hists else None

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        _render_histogram("📊 Histogram — Asli", cover_hist)
    with c2:
        _render_histogram("📊 Histogram — Terenkripsi", stego_hist)
    with c3:
        _render_evaluasi_metrik()


# ============================================================
# BARIS 3 — Uji Kunci Salah | Perbandingan Lapisan | Metode
# ============================================================

def _render_uji_kunci_salah() -> None:
    """Panel uji kunci salah: (a) password diubah 1 karakter, (b) 1 bit LSB diubah."""
    with st.container(key="card_row3_uji_kunci", border=True):
        st.markdown('<div class="card-title">🔑 Uji Kunci Salah</div>', unsafe_allow_html=True)

        # Jalankan uji jika flag di-set oleh toolbar
        run = st.session_state.pop("pixego_run_uji_kunci", False)
        result = st.session_state.get("pixego_uji_kunci_result")

        if run:
            stego = _img_from_session("pixego_stego_png")
            pw = st.session_state.get("pixego_embed_password", "")
            if stego is None or not pw:
                st.session_state["pixego_uji_kunci_result"] = {
                    "error": "Enkripsi gambar terlebih dahulu untuk menjalankan uji kunci."
                }
            else:
                # (a) Password diubah 1 karakter
                pw_salah = pw[:-1] + chr(ord(pw[-1]) + 1) if pw else "x"
                try:
                    extract_message(stego, pw_salah)
                    status_a = "LOLOS ⚠️"
                    badge_a = "pass"
                except core.StegoError:
                    status_a = "DITOLAK ✓"
                    badge_a = "rejected"

                # (b) 1 bit LSB gambar diubah
                arr = np.array(stego).reshape(-1).copy()
                # Ubah bit pertama setelah header
                arr[core.HEADER_BITS] ^= 1
                stego_rusak = Image.fromarray(arr.reshape(np.array(stego).shape))
                try:
                    extract_message(stego_rusak, pw)
                    status_b = "LOLOS ⚠️"
                    badge_b = "pass"
                except core.StegoError:
                    status_b = "DITOLAK ✓"
                    badge_b = "rejected"

                # Hitung metrik perbandingan stego vs stego_rusak
                mse_r = core.mse(stego, stego_rusak)
                psnr_r = core.psnr(stego, stego_rusak)
                ssim_r = met.ssim(stego, stego_rusak)
                ent_r = met.entropy(stego_rusak)
                uaci_r = met.uaci(stego, stego_rusak)

                st.session_state["pixego_uji_kunci_result"] = {
                    "status_a": status_a, "badge_a": badge_a,
                    "status_b": status_b, "badge_b": badge_b,
                    "mse": mse_r, "psnr": psnr_r,
                    "ssim": ssim_r, "ent": ent_r, "uaci": uaci_r,
                }
            result = st.session_state.get("pixego_uji_kunci_result")

        if result is None:
            st.caption("Klik tombol UJI KUNCI di toolbar untuk menjalankan.")
            return

        if "error" in result:
            st.error(result["error"], icon="⚠️")
            return

        # Tampilkan hasil
        sa, ba = result["status_a"], result["badge_a"]
        sb, bb = result["status_b"], result["badge_b"]
        st.markdown(
            f'<div style="margin-bottom:.35rem;">'
            f'<span style="font-size:.85rem;color:var(--muted);">Password salah (1 karakter): </span>'
            f'<span class="status-badge status-{ba}">{sa}</span>'
            f'</div>'
            f'<div style="margin-bottom:.45rem;">'
            f'<span style="font-size:.85rem;color:var(--muted);">Gambar diubah (1 bit LSB): </span>'
            f'<span class="status-badge status-{bb}">{sb}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        # Grid metrik 2 kolom
        grid_rows = [
            ("MSE", _fmt(result["mse"], ".6f")),
            ("PSNR (dB)", _fmt(result["psnr"], ".2f")),
            ("SSIM", _fmt(result["ssim"], ".4f")),
            ("Entropy", _fmt(result["ent"], ".4f")),
            ("UACI (%)", _fmt(result["uaci"], ".2f")),
        ]
        items_html = "".join(
            f'<div class="key-test-item">'
            f'<label>{r[0]}</label><br>'
            f'<span>{r[1]}</span>'
            f'</div>'
            for r in grid_rows
        )
        st.markdown(
            f'<div class="key-test-grid">{items_html}</div>'
            f'<p style="font-size:.82rem;color:var(--muted);margin-top:.35rem;">'
            f'Password salah atau gambar yang diubah akan ditolak saat dekripsi (tag AES-GCM tidak valid).</p>',
            unsafe_allow_html=True
        )


def _render_perbandingan_lapisan() -> None:
    """Panel perbandingan mode sekuensial vs acak menggunakan pesan acak 128 byte."""
    with st.container(key="card_row3_compare", border=True):
        st.markdown('<div class="card-title">⚖️ Perbandingan Lapisan</div>', unsafe_allow_html=True)

        result = st.session_state.get("pixego_compare_result")

        if st.button("Jalankan Perbandingan", key="btn_compare_run",
                     use_container_width=True):
            cover = _img_from_session("pixego_cover_png")
            if cover is None:
                st.error("Unggah gambar cover terlebih dahulu.", icon="⚠️")
            else:
                with st.spinner("Menjalankan dua mode penyisipan…"):
                    try:
                        rand_msg = os.urandom(128)
                        tmp_pw = os.urandom(16).hex()

                        t0 = time.perf_counter()
                        stego_seq, _ = embed_message(cover, rand_msg, tmp_pw, "sequential", 1)
                        t_seq = time.perf_counter() - t0

                        t0 = time.perf_counter()
                        stego_rnd, _ = embed_message(cover, rand_msg, tmp_pw, "random", 1)
                        t_rnd = time.perf_counter() - t0

                        st.session_state["pixego_compare_result"] = {
                            "mse_seq": core.mse(cover, stego_seq),
                            "psnr_seq": core.psnr(cover, stego_seq),
                            "ent_seq": met.entropy(stego_seq),
                            "chi_seq": core.chi_square_full(stego_seq),
                            "t_seq": t_seq * 1000,
                            "mse_rnd": core.mse(cover, stego_rnd),
                            "psnr_rnd": core.psnr(cover, stego_rnd),
                            "ent_rnd": met.entropy(stego_rnd),
                            "chi_rnd": core.chi_square_full(stego_rnd),
                            "t_rnd": t_rnd * 1000,
                            "ent_cover": met.entropy(cover),
                            "mse_cover": 0.0,
                            "psnr_cover": float("inf"),
                            "chi_cover": core.chi_square_full(cover),
                        }
                        result = st.session_state["pixego_compare_result"]
                    except core.StegoError as e:
                        st.error(str(e), icon="⚠️")
                    except Exception:
                        st.error("Perbandingan gagal.", icon="⚠️")

        if result is None:
            st.caption("Klik tombol di atas untuk membandingkan mode penyisipan.")
            return

        r = result
        # Tabel perbandingan
        compare_rows = [
            ("MSE", "0.000000", _fmt(r["mse_seq"], ".6f"), _fmt(r["mse_rnd"], ".6f")),
            ("PSNR (dB)", "∞", _fmt(r["psnr_seq"], ".2f"), _fmt(r["psnr_rnd"], ".2f")),
            ("Entropi", _fmt(r["ent_cover"], ".4f"), _fmt(r["ent_seq"], ".4f"), _fmt(r["ent_rnd"], ".4f")),
            ("Chi-sq (p)", _fmt(r["chi_cover"], ".4f"), _fmt(r["chi_seq"], ".4f"), _fmt(r["chi_rnd"], ".4f")),
            ("Embed (ms)", "—", _fmt(r["t_seq"], ".1f"), _fmt(r["t_rnd"], ".1f")),
        ]
        rows_html = "".join(
            f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td></tr>"
            for row in compare_rows
        )
        table_html = (
            '<table class="metrics-table">'
            '<thead><tr><th>Metrik</th><th>Cover</th><th>Sekuensial</th><th>Acak</th></tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            '</table>'
        )
        st.markdown(table_html, unsafe_allow_html=True)


def _render_metode_pengujian() -> None:
    """Panel metode pengujian: st.tabs dua tab (Metode & Temuan Notebook)."""
    with st.container(key="card_row3_metode", border=True):
        st.markdown('<div class="card-title">📖 Metode Pengujian</div>', unsafe_allow_html=True)

        # st.tabs HANYA di dalam kartu ini — sesuai aturan
        tab_metode, tab_temuan = st.tabs(["Metode", "Temuan Notebook"])

        with tab_metode:
            poin = [
                "Enkripsi AES-256-GCM dengan kunci dari Argon2id + HKDF.",
                "Penyisipan bit di LSB kanal RGB mode sekuensial / acak berbasis kunci.",
                "Evaluasi MSE, PSNR, SSIM, histogram, chi-square, entropi, korelasi, NPCR, UACI.",
                "Validasi: password salah atau gambar berubah → ditolak (tag AES-GCM tidak valid).",
                "Hasil ditampilkan dalam satu layar tanpa scroll.",
            ]
            for i, p in enumerate(poin, 1):
                st.markdown(
                    f'<div style="font-size:.9rem;margin-bottom:.32rem;">'
                    f'<span style="color:var(--accent-violet);font-weight:700;'
                    f'font-family:\'JetBrains Mono\',monospace;">{i}.</span> '
                    f'<span style="color:var(--secondary)">{p}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        with tab_temuan:
            _render_temuan_notebook()


def _render_temuan_notebook() -> None:
    """Ringkasan 4 angka penting dari CSV di folder notebook/."""
    from pathlib import Path
    notebook_dir = Path(__file__).resolve().parents[1] / "notebook"
    try:
        psnr_table = pd.read_csv(notebook_dir / "hasil_psnr.csv")
        chi_table = pd.read_csv(notebook_dir / "hasil_chi_square.csv")
        time_table = pd.read_csv(notebook_dir / "hasil_waktu.csv")

        t50_tex = chi_table[(chi_table["cover"] == "tekstur") &
                             (chi_table["penggunaan_kapasitas"] == "50%")].set_index("mode")["p_value"]
        median_embed = time_table.groupby("mode")["waktu_embed_s"].median()
        psnr_row = psnr_table[(psnr_table["cover"] == "tekstur") &
                               (psnr_table["bit"] == 1) &
                               (psnr_table["pesan_byte"] == 51200)]
        psnr_val = psnr_row["PSNR_dB"].median() if not psnr_row.empty else None

        temuan = [
            ("PSNR (tekstur, 50 KB, 1 bit)", _fmt(psnr_val, ".2f") + " dB"),
            ("p-value seq/acak (tekstur, 50%)",
             f'{_fmt(float(t50_tex.get("sequential", float("nan"))), ".4f")} / '
             f'{_fmt(float(t50_tex.get("random", float("nan"))), ".4f")}'),
            ("Median embed seq/acak",
             f'{_fmt(float(median_embed.get("sequential", float("nan"))), ".3f")} / '
             f'{_fmt(float(median_embed.get("random", float("nan"))), ".3f")} dtk'),
            ("p-value polos (50%)", "0.0000 (seq & acak)"),
        ]
        for label, val in temuan:
            st.markdown(
                f'<div style="font-size:.86rem;margin-bottom:.28rem;">'
                f'<span style="color:var(--muted)">{label}: </span>'
                f'<strong style="color:var(--ink)">{val}</strong>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.caption("Sumber: notebook/pixego.ipynb & CSV hasil eksperimen.")
    except (OSError, KeyError, ValueError, IndexError):
        st.caption("Ringkasan notebook belum tersedia (pastikan CSV ada di folder notebook/).")


def render_row3() -> None:
    """Baris 3: Uji Kunci Salah | Perbandingan Lapisan | Metode Pengujian."""
    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        _render_uji_kunci_salah()
    with c2:
        _render_perbandingan_lapisan()
    with c3:
        _render_metode_pengujian()


# ============================================================
# FOOTER
# ============================================================

def render_footer() -> None:
    """Satu baris footer sangat kecil."""
    st.markdown(
        f'<div class="op-footer">{FOOTER_TEXT}</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# ENTRY POINT
# ============================================================

def render_onepage() -> None:
    """Render seluruh halaman satu layar Pixego."""
    render_header()
    render_toolbar()
    render_row1()
    render_row2()
    render_row3()
    render_footer()
