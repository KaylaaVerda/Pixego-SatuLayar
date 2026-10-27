import streamlit as st

import io
import os
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

import stego_core as core
from app.components import footer, section_title, stat_card
from app.services import embed_message, load_cover_upload, load_stego_upload

st.title("Analisis Kualitas dan Steganalisis")
st.write("Bandingkan perubahan visual gambar dan lihat hasil uji statistik chi-square.")

def _session_image(key: str):
	data = st.session_state.get(key)
	return Image.open(io.BytesIO(data)).convert("RGB") if data else None


session_cover = _session_image("pixego_cover_png")
session_stego = _session_image("pixego_stego_png")
cover_upload = st.file_uploader("Unggah cover (opsional)", type=["png", "jpg", "jpeg", "bmp", "webp"], key="analysis_cover_upload")
stego_upload = st.file_uploader("Unggah stego PNG/BMP (opsional)", type=["png", "bmp", "jpg", "jpeg", "webp"], key="analysis_stego_upload")

cover = session_cover
stego = session_stego
try:
	if cover_upload:
		cover, was_resized = load_cover_upload(cover_upload)
		if was_resized:
			st.info("Cover besar diperkecil otomatis sampai sisi terpanjang 1024 piksel.")
	if stego_upload:
		stego = load_stego_upload(stego_upload, stego_upload.name)
except core.StegoError as error:
	st.error(str(error))
	cover, stego = None, None
except Exception:
	st.error("Gambar tidak dapat diproses.")
	cover, stego = None, None

if cover is not None and stego is not None:
	if cover.size != stego.size:
		st.warning("Ukuran cover dan stego berbeda. Metrik kualitas dan selisih tidak dapat dibandingkan.")
	else:
		section_title("Perbandingan Gambar")
		metrics = st.columns(2)
		with metrics[0]:
			st.metric("MSE", f"{core.mse(cover, stego):.6f}")
		with metrics[1]:
			st.metric("PSNR", f"{core.psnr(cover, stego):.2f} dB")
		image_columns = st.columns(2, gap="medium")
		with image_columns[0]:
			st.image(cover, caption="Cover", width="stretch")
			st.image(core.lsb_plane(cover), caption="Bidang LSB cover · kanal merah", width="stretch")
		with image_columns[1]:
			st.image(stego, caption="Stego", width="stretch")
			st.image(core.lsb_plane(stego), caption="Bidang LSB stego · kanal merah", width="stretch")

		hist_columns = st.columns(2)
		for column, image, label in (
			(hist_columns[0], cover, "Histogram kanal merah · cover"),
			(hist_columns[1], stego, "Histogram kanal merah · stego"),
		):
			with column:
				values = np.asarray(image.convert("RGB"))[:, :, 0]
				counts, edges = np.histogram(values, bins=64, range=(0, 256))
				st.caption(label)
				st.bar_chart(pd.DataFrame({"piksel": counts}, index=edges[:-1]))

		section_title("Kurva Chi-Square")
		cover_x, cover_p = core.chi_square_progressive(cover, steps=20)
		stego_x, stego_p = core.chi_square_progressive(stego, steps=20)
		chart = pd.DataFrame({"Cover": cover_p, "Stego": stego_p}, index=cover_x)
		chart.index.name = "Persentase piksel"
		st.line_chart(chart)
		st.caption("p-value yang mendekati 1 dapat dicurigai sebagai pola penyisipan, tetapi hasilnya sangat bergantung pada karakter gambar dan bukan bukti pasti.")
elif cover is not None:
	st.info("Unggah gambar stego PNG/BMP untuk membandingkan, atau jalankan perbandingan mode di bawah.")
else:
	st.info("Belum ada gambar dalam sesi ini. Unggah cover dan stego, atau gunakan perbandingan mode.")

st.divider()
section_title("Bandingkan Mode")
st.write("Gunakan satu cover dan pesan acak sementara berukuran 128 byte. Hasil perhitungan tidak disimpan.")
comparison_cover = cover if cover is not None else session_cover
comparison_upload = st.file_uploader("Pilih cover untuk perbandingan", type=["png", "jpg", "jpeg", "bmp", "webp"], key="analysis_compare_upload")
if comparison_upload:
	try:
		comparison_cover, was_resized = load_cover_upload(comparison_upload)
		if was_resized:
			st.info("Cover besar diperkecil otomatis sampai sisi terpanjang 1024 piksel.")
	except core.StegoError as error:
		st.error(str(error))
		comparison_cover = None
	except Exception:
		st.error("Cover tidak dapat diproses.")
		comparison_cover = None

if st.button("Jalankan perbandingan", disabled=comparison_cover is None):
	try:
		with st.spinner("Membuat dua contoh penyisipan dan menghitung chi-square..."):
			random_message = os.urandom(128)
			temporary_password = os.urandom(24).hex()
			sequential, _ = embed_message(comparison_cover, random_message, temporary_password, "sequential", 1)
			random_stego, _ = embed_message(comparison_cover, random_message, temporary_password, "random", 1)
			x_seq, p_seq = core.chi_square_progressive(sequential, steps=20)
			x_random, p_random = core.chi_square_progressive(random_stego, steps=20)
		chart = pd.DataFrame({"Sekuensial": p_seq, "Acak": p_random}, index=x_seq)
		chart.index.name = "Persentase piksel"
		st.line_chart(chart)
		st.caption("Ini contoh perbandingan statistik, bukan jaminan deteksi atau keamanan. Hasil chi-square bergantung pada gambar dan pesan.")
	except core.StegoError as error:
		st.error(str(error))
	except Exception:
		st.error("Perbandingan tidak dapat diselesaikan untuk gambar ini.")


def _notebook_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
	notebook_dir = Path(__file__).resolve().parents[2] / "notebook"
	return (
		pd.read_csv(notebook_dir / "hasil_psnr.csv"),
		pd.read_csv(notebook_dir / "hasil_chi_square.csv"),
		pd.read_csv(notebook_dir / "hasil_waktu.csv"),
	)


st.divider()
section_title("Temuan dari Notebook", "HASIL EKSPERIMEN TERSIMPAN")
st.markdown(
	'<div class="notebook-intro"><strong>Dua cover, dua cerita.</strong> '
	'Pada kapasitas yang sama, uji chi-square merespons berbeda pada cover tekstur dan cover polos. '
	'Ini menunjukkan mengapa satu angka saja tidak cukup untuk menilai stego.</div>',
	unsafe_allow_html=True,
)

try:
	psnr_table, chi_table, time_table = _notebook_tables()
	texture_50kb = psnr_table[
		(psnr_table["cover"] == "tekstur")
		& (psnr_table["bit"] == 1)
		& (psnr_table["pesan_byte"] == 51200)
	]
	texture_50 = chi_table[
		(chi_table["cover"] == "tekstur")
		& (chi_table["penggunaan_kapasitas"] == "50%")
	].set_index("mode")["p_value"]
	flat_50 = chi_table[
		(chi_table["cover"] == "polos")
		& (chi_table["penggunaan_kapasitas"] == "50%")
	].set_index("mode")["p_value"]
	median_embed = time_table.groupby("mode")["waktu_embed_s"].median()

	if texture_50kb.empty or not {"sequential", "random"}.issubset(texture_50.index):
		raise ValueError("Hasil eksperimen belum lengkap")
	psnr_value = texture_50kb["PSNR_dB"].median()
	usage_value = texture_50kb["penggunaan_%"].median()
	sequential_p = float(texture_50["sequential"])
	random_p = float(texture_50["random"])
	sequential_time = float(median_embed["sequential"])
	random_time = float(median_embed["random"])

	metric_columns = st.columns(4, gap="medium")
	for column, label, value, note in (
		(metric_columns[0], "PSNR · cover tekstur", f"{psnr_value:.2f} dB", f"1 bit/kanal · 50 KB · {usage_value:.2f}% kapasitas"),
		(metric_columns[1], "p-value · tekstur · 50%", f"{sequential_p:.4f} / {random_p:.4f}", "Sekuensial / acak"),
		(metric_columns[2], "p-value · polos · 50%", f"{float(flat_50['sequential']):.4f}", "Sekuensial dan acak sama-sama 0.0000"),
		(metric_columns[3], "Median embed", f"{sequential_time:.3f} / {random_time:.3f} dtk", "Sekuensial / acak · empat ukuran pesan"),
	):
		with column:
			stat_card(label, value, note)

	chart_columns = st.columns(2, gap="large")
	for column, cover_key, heading in (
		(chart_columns[0], "tekstur", "Cover tekstur"),
		(chart_columns[1], "polos", "Cover polos"),
	):
		cover_rows = chi_table[chi_table["cover"] == cover_key]
		base_rows = cover_rows[cover_rows["mode"] == "cover asli"]
		mode_rows = cover_rows[cover_rows["mode"].isin(["sequential", "random"])].copy()
		mode_rows["persen"] = mode_rows["penggunaan_kapasitas"].str.rstrip("%").astype(int)
		plot_data = mode_rows.pivot(index="persen", columns="mode", values="p_value").sort_index()
		plot_data = plot_data.rename(columns={"sequential": "Sekuensial", "random": "Acak"})
		if not base_rows.empty:
			plot_data["Cover asli"] = float(base_rows.iloc[0]["p_value"])
		with column:
			st.markdown(f'<div class="notebook-chart-title">{heading}</div>', unsafe_allow_html=True)
			plot_data.index.name = "Kapasitas terpakai (%)"
			st.line_chart(plot_data)

	texture_full = chi_table[
		(chi_table["cover"] == "tekstur")
		& (chi_table["penggunaan_kapasitas"] == "100%")
	].set_index("mode")["p_value"]
	st.markdown(
		'<div class="notebook-reading"><div class="notebook-reading-mark">BACA POLANYA</div>'
		'<div><strong>Mode acak tidak otomatis lolos steganalisis.</strong> Pada cover tekstur di 50% kapasitas, '
		f'p-value naik dari {sequential_p:.4f} ke {random_p:.4f}, tetapi pada 100% kapasitas keduanya mendekati 1 '
		f'({float(texture_full["sequential"]):.4f} sekuensial, {float(texture_full["random"]):.4f} acak). '
		'Pada cover polos, p-value masih 0.0000 di 50%. Karakter cover dan banyaknya data sama pentingnya dengan mode.</div>'
		'<div class="notebook-reading-note">p-value yang mendekati 1 dapat dicurigai sebagai jejak penyisipan. '
		'Ini satu uji statistik pada dua cover sintetis, bukan bukti aman atau tidak aman.</div></div>',
		unsafe_allow_html=True,
	)
	st.caption("Sumber: notebook/pixego.ipynb dan CSV hasil eksperimen. Waktu proses berasal dari satu sesi perangkat dan dapat berbeda di mesin lain.")
except (OSError, KeyError, ValueError, IndexError):
	st.info("Ringkasan notebook belum tersedia. Pastikan tiga CSV hasil eksperimen ada di folder notebook.")

footer()