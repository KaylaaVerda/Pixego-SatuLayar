"""
Unit test. Jalankan dari folder proyek:
    python -m unittest discover -s tests -v
"""
import io
import os
import sys
import unittest
from unittest import mock

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import stego_core as sc


def make_cover(w=160, h=160, seed=1):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    base = 128 + 80 * np.sin(x / 17.0) * np.cos(y / 23.0)
    img = np.stack([base, base * 0.8, 255 - base], axis=-1) + rng.normal(0, 5, (h, w, 3))
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


class TestRoundtrip(unittest.TestCase):
    def setUp(self):
        self.cover = make_cover()

    def test_semua_mode_dan_bit(self):
        for mode in ("sequential", "random"):
            for k in (1, 2, 3):
                msg = f"uji {mode} {k} bit " * 10
                st, _ = sc.embed(self.cover, msg, "pw-uji", mode=mode, bits=k)
                self.assertEqual(sc.extract(st, "pw-uji").decode(), msg)

    def test_roundtrip_lewat_file_png(self):
        st, _ = sc.embed(self.cover, "lewat png", "pw", mode="random")
        buf = io.BytesIO()
        st.save(buf, format="PNG")
        buf.seek(0)
        self.assertEqual(sc.extract(Image.open(buf), "pw"), b"lewat png")

    def test_pesan_kosong_dan_biner(self):
        st, _ = sc.embed(self.cover, b"", "pw")
        self.assertEqual(sc.extract(st, "pw"), b"")
        blob = os.urandom(300)
        st, _ = sc.embed(self.cover, blob, "pw", mode="sequential", bits=2)
        self.assertEqual(sc.extract(st, "pw"), blob)

    def test_embed_ulang_berbeda(self):
        a, _ = sc.embed(self.cover, "sama", "pw")
        b, _ = sc.embed(self.cover, "sama", "pw")
        self.assertFalse(np.array_equal(np.array(a), np.array(b)))


class TestKegagalan(unittest.TestCase):
    def setUp(self):
        self.cover = make_cover()
        self.stego, _ = sc.embed(self.cover, "rahasia", "pw-benar", mode="random")

    def test_password_salah(self):
        with self.assertRaises(sc.StegoError):
            sc.extract(self.stego, "pw-salah")

    def test_body_dirusak(self):
        arr = np.array(self.stego).reshape(-1).copy()
        arr[sc.HEADER_BITS:] ^= 1
        rusak = Image.fromarray(arr.reshape(np.array(self.stego).shape))
        with self.assertRaises(sc.StegoError):
            sc.extract(rusak, "pw-benar")

    def test_header_dirusak(self):
        arr = np.array(self.stego).reshape(-1).copy()
        arr[:8] ^= 1
        rusak = Image.fromarray(arr.reshape(np.array(self.stego).shape))
        with self.assertRaises(sc.StegoError):
            sc.extract(rusak, "pw-benar")

    def test_jpeg_merusak_pesan(self):
        buf = io.BytesIO()
        self.stego.save(buf, format="JPEG", quality=95)
        buf.seek(0)
        with self.assertRaises(sc.StegoError):
            sc.extract(Image.open(buf), "pw-benar")

    def test_melebihi_kapasitas(self):
        besar = os.urandom(sc.capacity_bytes(self.cover.size, 1) + 1)
        with self.assertRaises(sc.StegoError):
            sc.embed(self.cover, besar, "pw", bits=1)

    def test_tanpa_pesan(self):
        with self.assertRaises(sc.StegoError):
            sc.extract(self.cover, "pw")

    def test_input_tidak_valid(self):
        with self.assertRaises(sc.StegoError):
            sc.embed(self.cover, "x", "")
        with self.assertRaises(sc.StegoError):
            sc.embed(self.cover, "x", "pw", mode="lain")
        with self.assertRaises(sc.StegoError):
            sc.embed(self.cover, "x", "pw", bits=4)


class TestLoadCover(unittest.TestCase):
    def _simpan(self, img, fmt, **kw):
        buf = io.BytesIO()
        img.save(buf, format=fmt, **kw)
        buf.seek(0)
        return buf

    def test_png_transparan_diratakan_di_atas_putih(self):
        buf = self._simpan(Image.new("RGBA", (30, 30), (0, 0, 0, 0)), "PNG")
        arr = np.array(sc.load_cover(buf))
        self.assertTrue((arr == 255).all())

    def test_rotasi_exif_diterapkan(self):
        exif = Image.Exif()
        exif[0x0112] = 6
        buf = self._simpan(Image.new("RGB", (40, 20), (10, 20, 30)), "JPEG", exif=exif)
        self.assertEqual(sc.load_cover(buf).size, (20, 40))

    def test_gambar_palet_jadi_rgb(self):
        pal = Image.new("RGB", (20, 20), (200, 10, 10)).convert("P")
        buf = self._simpan(pal, "PNG")
        self.assertEqual(sc.load_cover(buf).mode, "RGB")

    def test_pengecilan_otomatis_menjaga_rasio(self):
        buf = self._simpan(Image.new("RGB", (400, 200)), "PNG")
        img = sc.load_cover(buf, max_side=100)
        self.assertEqual(img.size, (100, 50))

    def test_tidak_diperbesar_jika_sudah_kecil(self):
        buf = self._simpan(Image.new("RGB", (50, 30)), "PNG")
        self.assertEqual(sc.load_cover(buf, max_side=100).size, (50, 30))

    def test_file_bukan_gambar(self):
        with self.assertRaises(sc.StegoError):
            sc.load_cover(io.BytesIO(b"ini bukan gambar"))

    def test_file_tidak_ada(self):
        with self.assertRaises(sc.StegoError):
            sc.load_cover("/path/yang/tidak/ada.png")

    def test_cover_jpg_bisa_dipakai_dan_hasil_png_lolos(self):
        jpg = self._simpan(make_cover(), "JPEG", quality=90)
        cover = sc.load_cover(jpg)
        st, _ = sc.embed(cover, "dari cover jpg", "pw")
        png = self._simpan(st, "PNG")
        self.assertEqual(sc.extract(Image.open(png), "pw"), b"dari cover jpg")


class TestBatas(unittest.TestCase):
    def test_gambar_terlalu_kecil_untuk_header(self):
        with self.assertRaises(sc.StegoError):
            sc.embed(Image.new("RGB", (8, 8)), "x", "pw")

    def test_mode_acak_menolak_gambar_terlalu_besar(self):
        cover = make_cover()
        with mock.patch.object(sc, "MAX_RANDOM_CHANNELS", 100):
            with self.assertRaises(sc.StegoError):
                sc.embed(cover, "x", "pw", mode="random")
            st, _ = sc.embed(cover, "x", "pw", mode="sequential")
            self.assertEqual(sc.extract(st, "pw"), b"x")

    def test_extract_acak_menolak_gambar_terlalu_besar(self):
        cover = make_cover()
        st, _ = sc.embed(cover, "x", "pw", mode="random")
        with mock.patch.object(sc, "MAX_RANDOM_CHANNELS", 100):
            with self.assertRaises(sc.StegoError):
                sc.extract(st, "pw")


class TestMetrik(unittest.TestCase):
    def test_gambar_identik(self):
        c = make_cover()
        self.assertEqual(sc.mse(c, c), 0.0)
        self.assertEqual(sc.psnr(c, c), float("inf"))

    def test_psnr_turun_saat_bit_naik(self):
        c = make_cover()
        msg = os.urandom(3000)
        p = []
        for k in (1, 2, 3):
            st, _ = sc.embed(c, msg, "pw", mode="random", bits=k)
            p.append(sc.psnr(c, st))
        self.assertGreater(p[0], p[1])
        self.assertGreater(p[1], p[2])

    def test_posisi_acak_deterministik(self):
        key = os.urandom(32)
        a = sc.random_positions(key, 5000, 800)
        b = sc.random_positions(key, 5000, 800)
        self.assertTrue(np.array_equal(a, b))
        self.assertEqual(len(set(a.tolist())), 800)


if __name__ == "__main__":
    unittest.main()
