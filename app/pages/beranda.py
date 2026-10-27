import base64
import math

import streamlit as st

from app.components import footer, icon_svg, pill, section_title, wordmark
from app.demo import home_demo


def _mini_curve(values: list[float], color: str) -> str:
	valid = [0.0 if not math.isfinite(value) else value for value in values]
	points = " ".join(
		f"{index * 100 / max(1, len(valid) - 1):.1f},{38 - max(0, min(1, value)) * 32:.1f}"
		for index, value in enumerate(valid)
	)
	return (
		'<svg class="mini-curve" viewBox="0 0 100 42" role="img" aria-label="Kurva chi-square contoh">'
		f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" '
		'stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>'
		'</svg>'
	)


def _image_data(data: bytes) -> str:
	return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


demo = home_demo()
wordmark()
badge_columns = st.columns(3, gap="small")
for column, (label, icon, tone) in zip(badge_columns, (
	("Steganografi LSB", "eye", "blue"),
	("AES-256-GCM + Argon2id", "lock", "violet"),
	("Analisis Chi-Square", "chart", "blue"),
)):
	with column:
		pill(label, icon, tone)

left, right = st.columns([1.08, .92], gap="large", vertical_alignment="center")
with left:
	st.markdown(
		'<h1 class="hero-title">Sembunyikan <span class="hero-highlight">Pesan Rahasia</span> di Dalam Gambar</h1>',
		unsafe_allow_html=True,
	)
	st.write(
		"Pixego mengenkripsi pesanmu dengan AES-256-GCM, lalu menyebarkannya ke piksel gambar. "
		"Hasilnya tampak seperti gambar biasa dan hanya bisa dibuka dengan password yang benar."
	)
	first, second = st.columns(2, gap="small")
	with first:
		st.page_link("app/pages/sembunyikan.py", label="Coba Sekarang", icon=":material/visibility_off:")
	with second:
		st.page_link("app/pages/analisis.py", label="Lihat Analisis", icon=":material/monitoring:")
	st.markdown(
		'<p class="hero-note">Pixego adalah proyek pembelajaran kriptografi, bukan alat keamanan untuk produksi.</p>',
		unsafe_allow_html=True,
	)

with right:
	cover_src = _image_data(demo["cover_png"])
	stego_src = _image_data(demo["stego_png"])
	st.markdown(
		'<div class="demo-stack">'
		'<article class="demo-card demo-card-main">'
		'<div class="demo-card-heading"><span>Contoh Penyisipan</span><span class="demo-dot">HASIL HITUNG</span></div>'
		f'<div class="demo-images"><img src="{cover_src}" alt="Gambar cover contoh"><img src="{stego_src}" alt="Gambar hasil contoh"></div>'
		f'<div class="demo-metrics"><span>MSE <b>{demo["mse"]:.4f}</b></span><span>PSNR <b>{demo["psnr"]:.2f} dB</b></span><span>Kapasitas <b>{demo["capacity"]:,} byte</b></span></div>'
		'</article>'
		'<article class="demo-card demo-card-process">'
		'<div class="demo-card-heading"><span>Alur Enkripsi</span></div>'
		'<div class="process-flow"><span>Password</span><i>›</i><span>Argon2id</span><i>›</i><span>AES-256-GCM</span><i>›</i><span>LSB acak</span><i>›</i><span>Stego PNG</span></div>'
		f'<div class="floating-lock">{icon_svg("lock", 22)}</div>'
		'</article>'
		'<article class="demo-card demo-card-chart">'
		'<div class="demo-card-heading"><span>Perbandingan Mode</span><span class="demo-dot">CONTOH</span></div>'
		f'<div class="chart-row"><span>Sekuensial</span>{_mini_curve(demo["sequential_p"], "#4b5170")}</div>'
		f'<div class="chart-row"><span>Acak</span>{_mini_curve(demo["random_p"], "#0f9d8a")}</div>'
		'</article></div>',
		unsafe_allow_html=True,
	)

st.write("")
features = [
	("shield", "Enkripsi terautentikasi", "AES-GCM memeriksa password dan keutuhan gambar."),
	("key", "Posisi acak berbasis kunci", "Urutan kanal mengikuti kunci turunan password."),
	("lock", "Penolakan saat tidak cocok", "Password salah atau gambar berubah akan ditolak."),
	("chart", "Analisis menyeluruh", "Lihat kualitas gambar dan uji chi-square."),
]
feature_columns = st.columns(4, gap="medium")
for column, (icon, title, description) in zip(feature_columns, features):
	with column:
		st.markdown(
			f'<div class="feature-card"><span class="feature-icon">{icon_svg(icon)}</span>'
			f'<h3>{title}</h3><p>{description}</p></div>',
			unsafe_allow_html=True,
		)

st.write("")
section_title("Cara Kerja", "PANDUAN SINGKAT")
hide_col, reveal_col = st.columns(2, gap="large")
with hide_col:
	st.markdown(
		'<div class="path-card"><div class="path-index">01</div><h3>Mau menyembunyikan pesan?</h3>'
		'<ol><li>Buka halaman Sembunyikan dan unggah gambar cover.</li>'
		'<li>Tulis pesanmu, isi password, lalu pilih mode penyisipan.</li>'
		'<li>Unduh gambar hasil (PNG) dan kirim sebagai file, bukan sebagai foto lewat chat.</li></ol></div>',
		unsafe_allow_html=True,
	)
	st.page_link("app/pages/sembunyikan.py", label="Buka Halaman Sembunyikan", icon=":material/visibility_off:")
with reveal_col:
	st.markdown(
		'<div class="path-card"><div class="path-index">02</div><h3>Mau mengungkap pesan?</h3>'
		'<ol><li>Buka halaman Ekstrak dan unggah gambar hasil dari Pixego (PNG atau BMP).</li>'
		'<li>Masukkan password yang sama dengan saat menyembunyikan.</li>'
		'<li>Pesan rahasia muncul. Password salah atau gambar yang sudah diubah akan ditolak.</li></ol></div>',
		unsafe_allow_html=True,
	)
	st.page_link("app/pages/ekstrak.py", label="Buka Halaman Ekstrak", icon=":material/lock_open:")

st.markdown(
	'<div class="limits-card"><span class="page-kicker">BATASAN YANG PERLU KAMU TAHU</span>'
	'<p>JPG atau resize merusak pesan. Mode acak dibatasi ukuran gambar. Hasil chi-square bergantung pada jenis gambar.</p></div>',
	unsafe_allow_html=True,
)
footer()