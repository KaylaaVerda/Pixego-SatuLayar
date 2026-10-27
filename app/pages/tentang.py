import streamlit as st

from app.components import footer, section_title
from app.config import DEVELOPER

st.title("Tentang Pixego")
st.write(
	"Pixego adalah aplikasi pembelajaran steganografi gambar. Pesan dienkripsi lebih dulu, "
	"kemudian bitnya disisipkan ke kanal warna gambar dengan metode LSB."
)

section_title("Cara Kerja")
st.markdown(
	"""
	```text
	Pesan + password
		  ↓
	Argon2id → HKDF-SHA256
		  ↓
	AES-256-GCM + tag autentikasi
		  ↓
	Penyisipan LSB sekuensial atau acak berbasis kunci
		  ↓
	Gambar PNG
	```
	"""
)

section_title("Batasan dan Keamanan")
st.markdown(
	"""
	- Pixego adalah proyek pembelajaran, bukan alat keamanan untuk produksi.
	- JPG, perubahan ukuran, pemotongan, filter, dan pengeditan dapat merusak pesan.
	- Mode acak membatasi ukuran gambar untuk menjaga penggunaan memori.
	- Chi-square hanya satu uji statistik dan hasilnya bergantung pada gambar.
	- Jangan unggah data yang benar-benar sensitif. Aplikasi memproses gambar, pesan, dan password di memori sesi.
	"""
)

section_title("Referensi")
st.markdown(
	"""
	- Westfeld, A. dan Pfitzmann, A. (2000). *Attacks on Steganographic Systems*.
	- Böhme, R. dan Westfeld, A. (2004). *Exploiting Preserved Statistics for Steganalysis*.
	- RFC 9106. *Argon2 Memory-Hard Function for Password Hashing and Proof-of-Work Applications*.
	"""
)

section_title("Privasi")
st.write("Pixego tidak menyimpan file, password, atau pesan ke disk. Data gambar yang diperlukan untuk halaman Analisis hanya disimpan di memori sesi dan dapat dihapus dengan tombol di bagian bawah halaman.")

section_title("Pengembang")
rows = "".join(
	f'<div class="developer-row"><span>{label}</span><strong>{value}</strong></div>'
	for label, value in DEVELOPER.items()
)
st.markdown(f'<div class="developer-card">{rows}</div>', unsafe_allow_html=True)
footer()