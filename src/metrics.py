"""
metrics.py
Fungsi metrik kualitas dan keamanan steganografi untuk Pixego.
Hanya bergantung pada numpy dan scipy (sudah ada di requirements.txt).
Tidak ada dependensi baru.
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image
from scipy.ndimage import uniform_filter
from scipy.stats import entropy as _scipy_entropy


# ---------- Helper internal ----------

def _to_array(img: Image.Image) -> np.ndarray:
    """Konversi gambar PIL ke array uint8 shape (H, W, 3)."""
    return np.array(img.convert("RGB"), dtype=np.uint8)


# ---------- Fungsi publik ----------

def entropy(img: Image.Image) -> float:
    """
    Entropi Shannon gambar dalam bit per byte (semua kanal digabung).
    Nilai mendekati 8 berarti distribusi piksel seragam (karakteristik ciphertext).
    """
    flat = _to_array(img).reshape(-1)
    counts = np.bincount(flat, minlength=256).astype(np.float64)
    # Hapus bin kosong agar log tidak error
    nonzero = counts[counts > 0]
    prob = nonzero / nonzero.sum()
    return float(-np.sum(prob * np.log2(prob)))


def ssim(a: Image.Image, b: Image.Image) -> float:
    """
    Structural Similarity Index (SSIM) rata-rata tiga kanal RGB.
    Implementasi windowed pakai uniform_filter (scipy), tanpa library tambahan.
    Nilai 1.0 = identik, 0.0 = tidak mirip sama sekali.
    """
    arr_a = _to_array(a).astype(np.float64)
    arr_b = _to_array(b).astype(np.float64)

    # Konstanta stabilisasi SSIM (Ref: Wang et al., 2004)
    k1, k2, L = 0.01, 0.03, 255.0
    c1 = (k1 * L) ** 2
    c2 = (k2 * L) ** 2

    win = 11  # ukuran jendela

    ssim_channels = []
    for ch in range(3):
        x = arr_a[:, :, ch]
        y = arr_b[:, :, ch]
        mu_x = uniform_filter(x, win)
        mu_y = uniform_filter(y, win)
        mu_xx = uniform_filter(x * x, win)
        mu_yy = uniform_filter(y * y, win)
        mu_xy = uniform_filter(x * y, win)
        sig_x = mu_xx - mu_x ** 2
        sig_y = mu_yy - mu_y ** 2
        sig_xy = mu_xy - mu_x * mu_y
        num = (2 * mu_x * mu_y + c1) * (2 * sig_xy + c2)
        den = (mu_x ** 2 + mu_y ** 2 + c1) * (sig_x + sig_y + c2)
        ssim_channels.append(float(np.mean(num / den)))

    return float(np.mean(ssim_channels))


def npcr(a: Image.Image, b: Image.Image) -> float:
    """
    Number of Pixel Change Rate (%) antara dua gambar.
    Menghitung persentase piksel yang nilai byte-nya berbeda di semua kanal.
    Nilai tinggi = banyak perubahan (diharapkan tinggi untuk uji kunci salah).
    """
    arr_a = _to_array(a)
    arr_b = _to_array(b)
    changed = np.any(arr_a != arr_b, axis=2)  # (H, W) bool
    return float(100.0 * changed.sum() / changed.size)


def uaci(a: Image.Image, b: Image.Image) -> float:
    """
    Unified Average Changing Intensity (%) antara dua gambar.
    Rata-rata perbedaan intensitas dinormalisasi ke 255.
    Nilai ~33% menunjukkan distribusi acak (ideal untuk ciphertext).
    """
    arr_a = _to_array(a).astype(np.float64)
    arr_b = _to_array(b).astype(np.float64)
    return float(100.0 * np.mean(np.abs(arr_a - arr_b)) / 255.0)


def adjacent_correlation(img: Image.Image, n_sample: int = 5000) -> dict[str, float]:
    """
    Korelasi piksel bersebelahan pada arah Horizontal (H), Vertikal (V), Diagonal (D).
    Sampel ±n_sample pasang piksel acak agar cepat (tidak memroses seluruh gambar).
    Nilai mendekati 0 = distribusi acak; mendekati 1 = korelasi tinggi.
    """
    arr = _to_array(img).reshape(-1, 3).astype(np.float64)  # (N, 3)
    h, w = img.size[1], img.size[0]  # height, width

    rng = np.random.default_rng(42)

    def _corr_pair(idx1: np.ndarray, idx2: np.ndarray) -> float:
        """Korelasi Pearson dua indeks piksel (rata-rata 3 kanal)."""
        c_vals = []
        for ch in range(3):
            x = arr[idx1, ch]
            y = arr[idx2, ch]
            # Pearson manual agar tidak bergantung pada scipy.stats
            x_m = x - x.mean()
            y_m = y - y.mean()
            denom = math.sqrt((x_m ** 2).sum() * (y_m ** 2).sum())
            if denom == 0:
                c_vals.append(1.0)
            else:
                c_vals.append(float(np.dot(x_m, y_m) / denom))
        return float(np.mean(c_vals))

    total_px = h * w
    n = min(n_sample, total_px - max(w, h + 1))

    # Horizontal: piksel (r, c) dan (r, c+1)
    rows_h = rng.integers(0, h, size=n)
    cols_h = rng.integers(0, w - 1, size=n)
    idx_h1 = rows_h * w + cols_h
    idx_h2 = rows_h * w + cols_h + 1
    corr_h = _corr_pair(idx_h1, idx_h2)

    # Vertikal: piksel (r, c) dan (r+1, c)
    rows_v = rng.integers(0, h - 1, size=n)
    cols_v = rng.integers(0, w, size=n)
    idx_v1 = rows_v * w + cols_v
    idx_v2 = (rows_v + 1) * w + cols_v
    corr_v = _corr_pair(idx_v1, idx_v2)

    # Diagonal: piksel (r, c) dan (r+1, c+1)
    rows_d = rng.integers(0, h - 1, size=n)
    cols_d = rng.integers(0, w - 1, size=n)
    idx_d1 = rows_d * w + cols_d
    idx_d2 = (rows_d + 1) * w + cols_d + 1
    corr_d = _corr_pair(idx_d1, idx_d2)

    return {"H": corr_h, "V": corr_v, "D": corr_d}


def throughput_kbps(n_bytes: int, seconds: float) -> float:
    """
    Throughput dalam KB/s.
    n_bytes = ukuran data yang diproses, seconds = waktu proses.
    """
    if seconds <= 0:
        return float("inf")
    return float((n_bytes / 1024.0) / seconds)
