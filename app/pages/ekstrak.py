import streamlit as st

import stego_core as core
from app.components import footer
from app.services import extract_message, load_stego_upload

st.title("Ekstrak Pesan dari Gambar")
st.write("Ungkap pesan rahasia yang tersimpan di dalam gambar")

st.info("Gunakan file PNG atau BMP asli. JPG dan WebP mengubah piksel sehingga pesan tidak dapat dipulihkan.")
stego_file = st.file_uploader(
	"Pilih gambar stego",
	type=["png", "bmp", "jpg", "jpeg", "webp"],
	key="pixego_stego_upload",
)
password = st.text_input("Password", type="password", key="pixego_extract_password")

if stego_file is not None and st.button("Ekstrak pesan", type="primary", disabled=not password):
	try:
		stego = load_stego_upload(stego_file, stego_file.name)
		with st.spinner("Memeriksa gambar dan membuka pesan..."):
			message = extract_message(stego, password)
		try:
			text = message.decode("utf-8")
			if any(not char.isprintable() and char not in "\n\r\t" for char in text):
				raise UnicodeDecodeError("utf-8", message, 0, len(message), "data biner")
			st.success("Pesan berhasil diekstrak.")
			st.text_area("Pesan rahasia", value=text, height=180, disabled=True)
		except UnicodeDecodeError:
			st.success("Data biner berhasil diekstrak.")
			st.download_button(
				"Unduh data hasil",
				data=message,
				file_name="pesan.bin",
				mime="application/octet-stream",
			)
	except core.StegoError as error:
		st.error(str(error))
	except Exception:
		st.error("Gambar tidak dapat diproses. Pastikan file masih utuh lalu coba lagi.")

st.page_link("app/pages/sembunyikan.py", label="Mau menyembunyikan pesan? Buka halaman Sembunyikan", icon=":material/visibility_off:")
footer()