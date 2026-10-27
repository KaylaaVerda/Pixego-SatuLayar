"""
tests/test_metrics.py
Unit test untuk src/metrics.py
Jalankan: python -m pytest tests/test_metrics.py -v
"""

import os
import sys
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import metrics as m


def _make_img(w=64, h=64, seed=0) -> Image.Image:
    """Buat gambar acak deterministik untuk testing."""
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
    return Image.fromarray(arr)


def _make_uniform(w=64, h=64, val=128) -> Image.Image:
    """Buat gambar piksel seragam."""
    arr = np.full((h, w, 3), val, dtype=np.uint8)
    return Image.fromarray(arr)


class TestEntropy(unittest.TestCase):
    def test_range(self):
        """Entropi harus di rentang [0, 8]."""
        img = _make_img()
        e = m.entropy(img)
        self.assertGreaterEqual(e, 0.0)
        self.assertLessEqual(e, 8.0)

    def test_uniform_near_zero(self):
        """Gambar piksel seragam memiliki entropi mendekati 0."""
        img = _make_uniform(val=100)
        self.assertAlmostEqual(m.entropy(img), 0.0, places=5)

    def test_random_near_eight(self):
        """Gambar acak sempurna memiliki entropi mendekati 8."""
        # Buat gambar yang mendekati distribusi seragam
        arr = np.arange(256, dtype=np.uint8)
        arr = np.tile(arr, (64 * 3 * 3,))[:64 * 64 * 3].reshape(64, 64, 3)
        img = Image.fromarray(arr)
        self.assertGreater(m.entropy(img), 7.0)


class TestSSIM(unittest.TestCase):
    def test_identical(self):
        """SSIM gambar identik harus 1.0."""
        img = _make_img()
        result = m.ssim(img, img)
        self.assertAlmostEqual(result, 1.0, places=4)

    def test_range(self):
        """SSIM harus antara -1 dan 1."""
        a = _make_img(seed=1)
        b = _make_img(seed=2)
        result = m.ssim(a, b)
        self.assertGreaterEqual(result, -1.0)
        self.assertLessEqual(result, 1.0)

    def test_different_lower(self):
        """SSIM gambar berbeda harus lebih kecil dari 1."""
        a = _make_uniform(val=0)
        b = _make_uniform(val=255)
        result = m.ssim(a, b)
        self.assertLess(result, 1.0)


class TestNPCR(unittest.TestCase):
    def test_identical(self):
        """NPCR gambar identik harus 0.0."""
        img = _make_img()
        self.assertAlmostEqual(m.npcr(img, img), 0.0, places=5)

    def test_range(self):
        """NPCR harus antara 0 dan 100."""
        a = _make_img(seed=1)
        b = _make_img(seed=2)
        result = m.npcr(a, b)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 100.0)

    def test_all_different(self):
        """Dua gambar dengan semua piksel berbeda harus NPCR = 100."""
        a = _make_uniform(val=0)
        b = _make_uniform(val=255)
        self.assertAlmostEqual(m.npcr(a, b), 100.0, places=5)


class TestUACI(unittest.TestCase):
    def test_identical(self):
        """UACI gambar identik harus 0.0."""
        img = _make_img()
        self.assertAlmostEqual(m.uaci(img, img), 0.0, places=5)

    def test_range(self):
        """UACI harus antara 0 dan 100."""
        a = _make_img(seed=1)
        b = _make_img(seed=2)
        result = m.uaci(a, b)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 100.0)

    def test_max_difference(self):
        """UACI max = 100% ketika semua piksel bergeser 255."""
        a = _make_uniform(val=0)
        b = _make_uniform(val=255)
        self.assertAlmostEqual(m.uaci(a, b), 100.0, places=5)


class TestAdjacentCorrelation(unittest.TestCase):
    def test_keys(self):
        """Hasil harus punya key H, V, D."""
        img = _make_img()
        result = m.adjacent_correlation(img)
        self.assertIn("H", result)
        self.assertIn("V", result)
        self.assertIn("D", result)

    def test_range(self):
        """Nilai korelasi harus dalam rentang [-1, 1]."""
        img = _make_img()
        result = m.adjacent_correlation(img)
        for key, val in result.items():
            self.assertGreaterEqual(val, -1.0, f"Korelasi {key} di bawah -1")
            self.assertLessEqual(val, 1.0, f"Korelasi {key} di atas 1")

    def test_uniform_high_correlation(self):
        """Gambar piksel seragam harus punya korelasi tinggi (mendekati 1)."""
        img = _make_uniform(val=128)
        result = m.adjacent_correlation(img)
        for key, val in result.items():
            self.assertGreater(abs(val), 0.9, f"Korelasi {key} seharusnya tinggi pada gambar seragam")


class TestThroughput(unittest.TestCase):
    def test_positive(self):
        """Throughput harus positif."""
        result = m.throughput_kbps(1024, 0.5)
        self.assertGreater(result, 0.0)

    def test_value(self):
        """1024 byte dalam 1 detik = 1.0 KB/s."""
        self.assertAlmostEqual(m.throughput_kbps(1024, 1.0), 1.0, places=5)

    def test_zero_seconds(self):
        """Waktu 0 detik menghasilkan inf."""
        self.assertEqual(m.throughput_kbps(1024, 0), float("inf"))


if __name__ == "__main__":
    unittest.main()
