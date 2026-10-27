import streamlit as st

import stego_core as core
from app.components import footer, section_title
from app.services import (
	capacity_bytes,
	embed_message,
	image_to_png_bytes,
	load_cover_upload,
)

st.title("Sembunyikan Pesan ke Dalam Gambar")
st.write("Enkripsi pesan lalu sisipkan ke gambar. Gambar hasil selalu disimpan sebagai PNG.")

cover_file = st.file_uploader(
	"Pilih gambar cover",
	type=["png", "jpg", "jpeg", "bmp", "webp"],
	key="pixego_cover_upload",
)

cover = None
if cover_file is not None:
	try:
		cover, resized = load_cover_upload(cover_file)
		st.image(cover, caption=f"Cover siap dipakai · {cover.width} × {cover.height}", width="stretch")
		if resized:
			st.info("Gambar besar diperkecil otomatis sampai sisi terpanjang 1024 piksel.")
	except core.StegoError as error:
		st.error(str(error))
	except Exception:
		st.error("Gambar tidak dapat diproses. Periksa file lalu coba lagi.")

message = st.text_area(
	"Pesan rahasia",
	placeholder="Tulis pesan yang ingin disembunyikan",
	height=150,
	key="pixego_message",
)
password = st.text_input(
	"Password",
	type="password",
	key="pixego_embed_password",
	help="Gunakan password panjang dan unik.",
)
st.caption(f"Panjang password: {len(password)} karakter")

mode_label = st.radio(
	"Mode penyisipan",
	["Acak berbasis kunci", "Sekuensial"],
	horizontal=True,
	key="pixego_embed_mode",
)
mode = "random" if mode_label == "Acak berbasis kunci" else "sequential"
bits = st.select_slider("Bit per kanal", options=[1, 2, 3], value=1, key="pixego_embed_bits")

if cover is not None:
	capacity = capacity_bytes(cover.size, bits)
	message_bytes = len(message.encode("utf-8"))
	usage = 100 * message_bytes / max(capacity, 1)
	st.progress(min(usage / 100, 1.0), text=f"Kapasitas terpakai: {usage:.2f}% · {message_bytes} / {capacity} byte")
	if message_bytes > capacity:
		st.warning("Pesan terlalu panjang untuk gambar dan pengaturan ini.")

if st.button("Proses dan sembunyikan", type="primary", disabled=cover is None or not password or not message):
	try:
		with st.spinner("Mengenkripsi pesan dan menyisipkannya ke gambar..."):
			stego, info = embed_message(cover, message, password, mode, bits)
			cover_png = image_to_png_bytes(cover)
			stego_png = image_to_png_bytes(stego)
		st.session_state["pixego_cover_png"] = cover_png
		st.session_state["pixego_stego_png"] = stego_png
		st.session_state["pixego_last_info"] = info
		st.success("Pesan berhasil disisipkan.")
		st.session_state["pixego_result_ready"] = True
	except core.StegoError as error:
		st.error(str(error))
		st.session_state.pop("pixego_result_ready", None)
	except Exception:
		st.error("Proses gagal. Periksa input lalu coba lagi.")
		st.session_state.pop("pixego_result_ready", None)

if st.session_state.get("pixego_result_ready") and st.session_state.get("pixego_stego_png"):
	import io
	from PIL import Image

	saved_cover = Image.open(io.BytesIO(st.session_state["pixego_cover_png"])).convert("RGB")
	saved_stego = Image.open(io.BytesIO(st.session_state["pixego_stego_png"])).convert("RGB")
	section_title("Hasil Penyisipan")
	original_column, stego_column = st.columns(2, gap="medium")
	with original_column:
		st.image(saved_cover, caption="Cover", width="stretch")
	with stego_column:
		st.image(saved_stego, caption="Stego PNG", width="stretch")

	metrics = st.columns(2)
	with metrics[0]:
		st.metric("MSE", f"{core.mse(saved_cover, saved_stego):.6f}")
	with metrics[1]:
		st.metric("PSNR", f"{core.psnr(saved_cover, saved_stego):.2f} dB")
	st.image(core.difference_image(saved_cover, saved_stego), caption="Perbedaan piksel yang diperkuat", width="stretch")
	st.subheader("Info penyisipan")
	st.json(st.session_state["pixego_last_info"])
	st.download_button(
		"Unduh stego.png",
		data=st.session_state["pixego_stego_png"],
		file_name="stego.png",
		mime="image/png",
		type="primary",
	)
	st.warning("Kirim gambar hasil sebagai file atau dokumen, bukan sebagai foto lewat chat. Kompresi dan perubahan ukuran dapat merusak pesan.")

st.page_link("app/pages/ekstrak.py", label="Mau mengungkap pesan? Buka halaman Ekstrak", icon=":material/lock_open:")
footer()