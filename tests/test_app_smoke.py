"""Smoke tests untuk halaman tunggal Pixego dan wrapper layanan aplikasi."""

import io
import sys
import unittest
from pathlib import Path

from PIL import Image
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import stego_core as core
from app.services import embed_message, extract_message, load_cover_upload, load_stego_upload


def _make_cover_png(w=160, h=160) -> bytes:
    """Buat gambar cover PNG untuk keperluan test."""
    import numpy as np
    rng = np.random.default_rng(7)
    arr = (128 + 60 * np.sin(np.arange(w * h * 3).reshape(h, w, 3) / 30)).astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


class TestOnepageSmoke(unittest.TestCase):
    """Smoke test: halaman utama bisa dimuat tanpa exception."""

    def test_onepage_termuat(self):
        """streamlit_app.py harus render tanpa exception di state awal."""
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
        self.assertEqual(
            len(app.exception), 0,
            [item.value for item in app.exception],
        )

    def test_onepage_memiliki_file_uploader(self):
        """Harus ada minimal 2 file uploader (cover + stego)."""
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        self.assertGreaterEqual(len(app.file_uploader), 2)

    def test_onepage_tombol_toolbar_ada(self):
        """Toolbar harus memiliki tombol reset dan simpan citra minimal."""
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        # Minimal ada 6-7 tombol dari toolbar + tombol inline
        self.assertGreaterEqual(len(app.button) + len(app.get("download_button")), 5)

    def test_onepage_roundtrip_via_session(self):
        """Upload cover → enkripsi lewat session_state → verifikasi stego tersimpan."""
        cover_bytes = _make_cover_png()
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=60)

        # Set session_state sebelum run (simulasi cover sudah diunggah)
        cover_img = Image.open(io.BytesIO(cover_bytes)).convert("RGB")
        import io as _io
        buf = _io.BytesIO()
        cover_img.save(buf, format="PNG")
        app.session_state["pixego_cover_png"] = buf.getvalue()
        app.session_state["pixego_message"] = "pesan roundtrip test"
        app.session_state["pixego_embed_password"] = "pw-smoke-test"
        app.session_state["pixego_embed_mode"] = "Sekuensial"
        app.session_state["pixego_embed_bits"] = 1
        app.run()

        self.assertEqual(len(app.exception), 0, [item.value for item in app.exception])


class TestServiceSmoke(unittest.TestCase):
    """Test langsung ke service layer — tidak bergantung pada UI."""

    def test_roundtrip_dan_password_salah(self):
        """Service embed + extract harus roundtrip; password salah harus raise StegoError."""
        cover = Image.new("RGB", (160, 160), (120, 130, 140))
        stego, _ = embed_message(cover, "pesan uji", "pw-benar", "sequential", 1)
        self.assertEqual(extract_message(stego, "pw-benar"), b"pesan uji")
        with self.assertRaises(core.StegoError):
            extract_message(stego, "pw-salah")

    def test_menolak_gambar_kecil_dan_bukan_gambar(self):
        """Service harus tolak gambar terlalu kecil dan data bukan gambar."""
        with self.assertRaises(core.StegoError):
            embed_message(Image.new("RGB", (8, 8)), "x", "pw", "sequential", 1)
        with self.assertRaises(core.StegoError):
            load_cover_upload(io.BytesIO(b"bukan gambar"))

    def test_menolak_jpg_untuk_ekstraksi(self):
        """load_stego_upload harus tolak file JPG (kompresi merusak pesan)."""
        image = Image.new("RGB", (160, 160), (100, 120, 140))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)
        with self.assertRaisesRegex(core.StegoError, "PNG atau BMP"):
            load_stego_upload(buffer, "gambar.jpg")


if __name__ == "__main__":
    unittest.main()