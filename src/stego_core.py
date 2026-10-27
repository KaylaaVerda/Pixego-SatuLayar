"""
stego_core.py
Pixego: inti steganografi LSB (sekuensial dan acak berbasis kunci) dengan enkripsi AES-256-GCM.
Kode ini identik dengan yang ada di notebook, dipisah agar bisa dipakai oleh CLI dan unit test.
"""
import os
import io
import math
import time
import struct

import numpy as np
from PIL import Image, ImageOps
from scipy.stats import chi2 as chi2_dist

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag
from argon2.low_level import hash_secret_raw, Type


# Parameter Argon2id (cek ulang ke RFC 9106 dan OWASP sebelum dipakai di laporan)
ARGON2_TIME_COST = 3
ARGON2_MEMORY_KIB = 64 * 1024     # 64 MiB
ARGON2_PARALLELISM = 4
KEY_LEN = 32                      # 256 bit

# Parameter AES-GCM
NONCE_LEN = 12
TAG_LEN = 16

# Format header stego
MAGIC = b"STG1"
SALT_LEN = 16
HEADER_FMT = ">4sBB16sI"          # magic, mode, bits, salt, panjang body
HEADER_LEN = struct.calcsize(HEADER_FMT)   # 26 byte
HEADER_BITS = HEADER_LEN * 8               # 208 bit

MODE_SEQUENTIAL = 0
MODE_RANDOM = 1
MODE_NAMES = {"sequential": MODE_SEQUENTIAL, "random": MODE_RANDOM}

# Batas jumlah kanal untuk mode acak (sekitar 8 megapiksel) agar memori tidak habis
MAX_RANDOM_CHANNELS = 24_000_000



class StegoError(Exception):
    """Error khusus aplikasi: password salah, gambar rusak, kapasitas kurang, dan sebagainya."""


def derive_master_key(password: str, salt: bytes) -> bytes:
    """Password -> master key 32 byte memakai Argon2id."""
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_KIB,
        parallelism=ARGON2_PARALLELISM,
        hash_len=KEY_LEN,
        type=Type.ID,
    )


def derive_subkeys(master_key: bytes):
    """Master key -> (kunci AES, kunci posisi) memakai HKDF-SHA256 dengan label berbeda."""
    enc_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                   info=b"stego-enc-v1").derive(master_key)
    pos_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                   info=b"stego-pos-v1").derive(master_key)
    return enc_key, pos_key


def aes_gcm_encrypt(plaintext: bytes, enc_key: bytes, aad: bytes) -> bytes:
    """Mengembalikan nonce (12B) + ciphertext + tag (16B)."""
    nonce = os.urandom(NONCE_LEN)
    ciphertext_with_tag = AESGCM(enc_key).encrypt(nonce, plaintext, aad)
    return nonce + ciphertext_with_tag


def aes_gcm_decrypt(body: bytes, enc_key: bytes, aad: bytes) -> bytes:
    nonce, ciphertext_with_tag = body[:NONCE_LEN], body[NONCE_LEN:]
    try:
        return AESGCM(enc_key).decrypt(nonce, ciphertext_with_tag, aad)
    except InvalidTag:
        raise StegoError("Dekripsi gagal: password salah atau gambar sudah diubah.") from None


# ---------- Fungsi bantu bit ----------
def bytes_to_bits(data: bytes) -> np.ndarray:
    """bytes -> array bit (0/1), urutan MSB dulu."""
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def bits_to_bytes(bits: np.ndarray) -> bytes:
    return np.packbits(bits.astype(np.uint8)).tobytes()


def write_bits(flat: np.ndarray, positions: np.ndarray, bits: np.ndarray, k: int) -> None:
    """Tulis `bits` ke k bit terakhir kanal pada `positions` (in-place)."""
    pad = (-len(bits)) % k
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    groups = bits.reshape(-1, k)
    weights = (1 << np.arange(k - 1, -1, -1)).astype(np.uint8)
    values = (groups * weights).sum(axis=1).astype(np.uint8)
    pos = positions[:len(values)]
    clear_mask = np.uint8((0xFF << k) & 0xFF)
    flat[pos] = (flat[pos] & clear_mask) | values


def read_bits(flat: np.ndarray, positions: np.ndarray, k: int, n_bits: int) -> np.ndarray:
    """Baca n_bits dari k bit terakhir kanal pada `positions`."""
    n_channels = math.ceil(n_bits / k)
    values = flat[positions[:n_channels]] & np.uint8((1 << k) - 1)
    shifts = np.arange(k - 1, -1, -1).astype(np.uint8)
    bits = ((values[:, None] >> shifts) & 1).reshape(-1)
    return bits[:n_bits]


# ---------- Penentuan posisi ----------
def random_positions(pos_key: bytes, n_slots: int, n_needed: int) -> np.ndarray:
    """
    Urutan acak slot 0..n_slots-1 yang deterministik dari pos_key.
    Keystream AES-CTR -> satu angka uint64 per slot -> argsort stabil.
    """
    encryptor = Cipher(algorithms.AES(pos_key), modes.CTR(b"\x00" * 16)).encryptor()
    stream = encryptor.update(b"\x00" * (8 * n_slots)) + encryptor.finalize()
    randoms = np.frombuffer(stream, dtype="<u8")
    order = np.argsort(randoms, kind="stable")
    return order[:n_needed]


def body_positions(mode_id: int, pos_key: bytes, total_channels: int, n_needed: int) -> np.ndarray:
    n_slots = total_channels - HEADER_BITS
    if mode_id == MODE_SEQUENTIAL:
        return HEADER_BITS + np.arange(n_needed)
    return HEADER_BITS + random_positions(pos_key, n_slots, n_needed)


def capacity_bytes(size, bits: int = 1) -> int:
    """Kapasitas pesan (plaintext) dalam byte untuk gambar berukuran (lebar, tinggi)."""
    total_channels = size[0] * size[1] * 3
    raw = ((total_channels - HEADER_BITS) * bits) // 8
    return max(0, raw - NONCE_LEN - TAG_LEN)


def embed(cover: Image.Image, message, password: str, mode: str = "random", bits: int = 1):
    """
    Enkripsi `message` lalu sisipkan ke `cover`.
    Mengembalikan (stego_image, info).
    """
    if mode not in MODE_NAMES:
        raise StegoError("Mode harus 'sequential' atau 'random'.")
    if bits not in (1, 2, 3):
        raise StegoError("Bit per kanal harus 1, 2, atau 3.")
    if not password:
        raise StegoError("Password tidak boleh kosong.")

    plaintext = message.encode("utf-8") if isinstance(message, str) else bytes(message)

    arr = np.array(cover.convert("RGB"), dtype=np.uint8)
    shape = arr.shape
    flat = arr.reshape(-1).copy()
    total = flat.size
    if mode == "random" and total > MAX_RANDOM_CHANNELS:
        raise StegoError("Gambar terlalu besar untuk mode acak (batas sekitar 8 megapiksel). "
                         "Perkecil gambar dulu, atau pakai mode sequential.")

    body_len = NONCE_LEN + len(plaintext) + TAG_LEN
    channels_needed = math.ceil(body_len * 8 / bits)
    channels_free = total - HEADER_BITS
    if channels_needed > channels_free:
        cap = capacity_bytes(cover.size, bits)
        raise StegoError(f"Pesan terlalu panjang. Kapasitas maksimum {cap} byte "
                         f"untuk gambar ini dengan {bits} bit per kanal.")

    mode_id = MODE_NAMES[mode]
    salt = os.urandom(SALT_LEN)
    header = struct.pack(HEADER_FMT, MAGIC, mode_id, bits, salt, body_len)

    master = derive_master_key(password, salt)
    enc_key, pos_key = derive_subkeys(master)
    body = aes_gcm_encrypt(plaintext, enc_key, aad=header)

    # 1) header: sekuensial, 1 bit per kanal, di awal gambar
    write_bits(flat, np.arange(HEADER_BITS), bytes_to_bits(header), 1)
    # 2) body: posisi sesuai mode, k bit per kanal
    pos = body_positions(mode_id, pos_key, total, channels_needed)
    write_bits(flat, pos, bytes_to_bits(body), bits)

    stego = Image.fromarray(flat.reshape(shape))
    info = {
        "mode": mode,
        "bits_per_channel": bits,
        "ukuran_gambar": cover.size,
        "pesan_byte": len(plaintext),
        "body_byte": body_len,
        "kanal_dipakai": channels_needed,
        "kapasitas_byte": capacity_bytes(cover.size, bits),
        "penggunaan_kapasitas_%": round(100 * len(plaintext) / max(1, capacity_bytes(cover.size, bits)), 2),
    }
    return stego, info


def extract(stego: Image.Image, password: str) -> bytes:
    """Ekstrak dan dekripsi pesan. Melempar StegoError kalau gagal."""
    flat = np.array(stego.convert("RGB"), dtype=np.uint8).reshape(-1)
    total = flat.size
    if total <= HEADER_BITS:
        raise StegoError("Gambar terlalu kecil.")

    header = bits_to_bytes(flat[:HEADER_BITS] & 1)
    magic, mode_id, bits, salt, body_len = struct.unpack(HEADER_FMT, header)

    if magic != MAGIC:
        raise StegoError("Tidak ditemukan pesan tersembunyi (header tidak valid). "
                         "Mungkin gambar sudah dikompres atau diubah.")
    if mode_id not in (MODE_SEQUENTIAL, MODE_RANDOM) or bits not in (1, 2, 3):
        raise StegoError("Header rusak.")
    channels_needed = math.ceil(body_len * 8 / bits)
    if body_len < NONCE_LEN + TAG_LEN or channels_needed > total - HEADER_BITS:
        raise StegoError("Panjang data pada header tidak masuk akal.")
    if mode_id == MODE_RANDOM and total > MAX_RANDOM_CHANNELS:
        raise StegoError("Gambar terlalu besar untuk diproses pada mode acak. Perkecil gambar.")

    master = derive_master_key(password, salt)
    enc_key, pos_key = derive_subkeys(master)
    pos = body_positions(mode_id, pos_key, total, channels_needed)
    body = bits_to_bytes(read_bits(flat, pos, bits, body_len * 8))
    return aes_gcm_decrypt(body, enc_key, aad=header)


def to_array(img: Image.Image) -> np.ndarray:
    return np.array(img.convert("RGB"), dtype=np.uint8)


def mse(a: Image.Image, b: Image.Image) -> float:
    x = to_array(a).astype(np.float64)
    y = to_array(b).astype(np.float64)
    return float(np.mean((x - y) ** 2))


def psnr(a: Image.Image, b: Image.Image) -> float:
    m = mse(a, b)
    return float("inf") if m == 0 else 10 * math.log10(255.0 ** 2 / m)


def difference_image(a: Image.Image, b: Image.Image, gain: int = 255) -> Image.Image:
    """Selisih mutlak yang diperkuat supaya piksel berubah terlihat."""
    d = np.abs(to_array(a).astype(np.int16) - to_array(b).astype(np.int16))
    return Image.fromarray(np.clip(d * gain, 0, 255).astype(np.uint8))


def lsb_plane(img: Image.Image, channel: int = 0) -> Image.Image:
    """Bidang LSB satu kanal (hitam = 0, putih = 1). Dipakai untuk serangan visual."""
    return Image.fromarray(((to_array(img)[:, :, channel] & 1) * 255).astype(np.uint8))


def chi_square_test(values: np.ndarray, min_expected: float = 5.0):
    """
    Uji chi-square pasangan nilai (2i, 2i+1).
    Mengembalikan (p_value, statistik, jumlah_pasangan_dipakai).
    p mendekati 1 = dicurigai ada data tersembunyi.
    """
    hist = np.bincount(values, minlength=256).astype(np.float64)
    even, odd = hist[0::2], hist[1::2]
    expected = (even + odd) / 2.0
    keep = expected >= min_expected
    n_pairs = int(keep.sum())
    if n_pairs < 2:
        return float("nan"), float("nan"), n_pairs
    stat = float(np.sum((even[keep] - expected[keep]) ** 2 / expected[keep]))
    p = float(chi2_dist.sf(stat, n_pairs - 1))
    return p, stat, n_pairs


def chi_square_full(img: Image.Image) -> float:
    """p-value chi-square untuk seluruh gambar (semua kanal digabung)."""
    return chi_square_test(to_array(img).reshape(-1))[0]


def chi_square_progressive(img: Image.Image, steps: int = 20):
    """p-value pada x% data pertama, x = 5%, 10%, ..., 100%."""
    flat = to_array(img).reshape(-1)
    fractions = np.linspace(1 / steps, 1.0, steps)
    p_values = [chi_square_test(flat[:int(f * len(flat))])[0] for f in fractions]
    return fractions * 100, np.array(p_values)


def load_cover(source, max_side=None) -> Image.Image:
    """
    Membuka gambar COVER dengan aman. `source` boleh path file atau file-like object.
    - Rotasi EXIF diterapkan (foto HP sering tersimpan miring dengan info rotasi di EXIF).
    - Transparansi (alpha) diratakan di atas latar putih.
    - Palet warna (GIF, PNG 8-bit) diubah ke RGB. GIF animasi hanya frame pertama.
    - Kalau max_side diisi dan gambar lebih besar, gambar diperkecil dengan rasio tetap.
    Jangan pakai fungsi ini untuk STEGO image, karena rotasi atau resize merusak pesan.
    """
    try:
        img = Image.open(source)
        img = ImageOps.exif_transpose(img)
        has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
        if has_alpha:
            rgba = img.convert("RGBA")
            background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            img = Image.alpha_composite(background, rgba).convert("RGB")
        else:
            img = img.convert("RGB")
    except StegoError:
        raise
    except Exception as e:
        raise StegoError(f"Gambar tidak bisa dibuka ({type(e).__name__}). "
                         "Format HEIC/HEIF perlu dikonversi ke PNG atau JPG dulu.") from None
    if max_side and max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.LANCZOS)
    return img
