"""Smoke tests untuk route Streamlit dan wrapper layanan aplikasi."""

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


class TestAppSmoke(unittest.TestCase):
    def test_semua_halaman_termuat(self):
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=60).run()
        self.assertEqual(len(app.exception), 0, [item.value for item in app.exception])
        for page_path in (
            "app/pages/sembunyikan.py",
            "app/pages/ekstrak.py",
            "app/pages/analisis.py",
            "app/pages/tentang.py",
            "app/pages/beranda.py",
        ):
            app.switch_page(page_path).run()
            self.assertEqual(len(app.exception), 0, [item.value for item in app.exception])

    def test_analisis_memuat_temuan_notebook(self):
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=60).run()
        app.switch_page("app/pages/analisis.py").run()
        self.assertEqual(len(app.exception), 0, [item.value for item in app.exception])
        rendered_markdown = "\n".join(item.value for item in app.markdown)
        self.assertIn("Temuan dari Notebook", rendered_markdown)
        self.assertIn("53.97 dB", rendered_markdown)
        self.assertIn("0.1877 / 0.3647", rendered_markdown)
        self.assertEqual(len(app.get("vega_lite_chart")), 2)

    def test_roundtrip_lewat_ui_sembunyikan_dan_ekstrak(self):
        cover_buffer = io.BytesIO()
        Image.new("RGB", (160, 160), (120, 130, 140)).save(cover_buffer, format="PNG")
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=60).run()
        app.switch_page("app/pages/sembunyikan.py").run()
        app.file_uploader[0].upload("cover.png", cover_buffer.getvalue(), "image/png").run()
        app.text_area[0].set_value("roundtrip dari UI")
        app.text_input[0].set_value("pw-ui-uji")
        app.radio[0].set_value("Sekuensial")
        app.run()
        app.button[0].click().run()
        self.assertEqual(len(app.exception), 0, [item.value for item in app.exception])
        stego_png = app.session_state["pixego_stego_png"]

        app.switch_page("app/pages/ekstrak.py").run()
        app.file_uploader[0].upload("stego.png", stego_png, "image/png").run()
        app.text_input[0].set_value("pw-ui-uji")
        app.run()
        app.button[0].click().run()
        self.assertEqual(len(app.exception), 0, [item.value for item in app.exception])
        self.assertIn("roundtrip dari UI", [item.value for item in app.text_area])

    def test_service_roundtrip_dan_password_salah(self):
        cover = Image.new("RGB", (160, 160), (120, 130, 140))
        stego, _ = embed_message(cover, "pesan uji", "pw-benar", "sequential", 1)
        self.assertEqual(extract_message(stego, "pw-benar"), b"pesan uji")
        with self.assertRaises(core.StegoError):
            extract_message(stego, "pw-salah")

    def test_service_menolak_gambar_kecil_dan_file_bukan_gambar(self):
        with self.assertRaises(core.StegoError):
            embed_message(Image.new("RGB", (8, 8)), "x", "pw", "sequential", 1)
        with self.assertRaises(core.StegoError):
            load_cover_upload(io.BytesIO(b"bukan gambar"))

    def test_service_menolak_jpg_untuk_ekstraksi(self):
        image = Image.new("RGB", (160, 160), (100, 120, 140))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)
        with self.assertRaisesRegex(core.StegoError, "PNG atau BMP"):
            load_stego_upload(buffer, "gambar.jpg")


if __name__ == "__main__":
    unittest.main()