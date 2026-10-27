"""Pembungkus layanan steganografi dan konversi gambar."""

from __future__ import annotations

import io
import threading

from PIL import Image

import stego_core as core

ARGON2_SEMAPHORE = threading.Semaphore(2)
MAX_COVER_SIDE = 1024


def embed_message(cover: Image.Image, message: str | bytes, password: str, mode: str, bits: int):
    with ARGON2_SEMAPHORE:
        return core.embed(cover, message, password, mode=mode, bits=bits)


def extract_message(stego: Image.Image, password: str) -> bytes:
    with ARGON2_SEMAPHORE:
        return core.extract(stego, password)


def load_cover_upload(source) -> tuple[Image.Image, bool]:
    data = source.getvalue() if hasattr(source, "getvalue") else source.read()
    try:
        with Image.open(io.BytesIO(data)) as original:
            original_size = original.size
    except Exception:
        return core.load_cover(io.BytesIO(data), max_side=MAX_COVER_SIDE), False
    cover = core.load_cover(io.BytesIO(data), max_side=MAX_COVER_SIDE)
    return cover, max(original_size) > MAX_COVER_SIDE


def load_stego_upload(source, filename: str = "") -> Image.Image:
    """Buka PNG/BMP apa adanya. Jangan menerapkan orientasi atau resize pada stego."""
    data = source.getvalue() if hasattr(source, "getvalue") else source.read()
    try:
        with Image.open(io.BytesIO(data)) as image:
            image_format = (image.format or "").upper()
            if image_format not in {"PNG", "BMP"}:
                raise core.StegoError("Gambar stego harus berformat PNG atau BMP. JPG dan WebP mengubah piksel sehingga pesan rusak.")
            return image.convert("RGB").copy()
    except core.StegoError:
        raise
    except Exception:
        suffix = filename.rsplit(".", 1)[-1].upper() if "." in filename else ""
        if suffix in {"JPG", "JPEG", "WEBP"}:
            raise core.StegoError("Format JPG dan WebP tidak didukung untuk ekstraksi. Unggah file PNG atau BMP asli.") from None
        raise core.StegoError("File tidak dapat dibaca sebagai gambar PNG atau BMP.") from None


def image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def capacity_bytes(size: tuple[int, int], bits: int) -> int:
    return core.capacity_bytes(size, bits)


def clear_session_data(session_state) -> None:
    for key in (
        "pixego_cover_png", "pixego_stego_png", "pixego_last_info",
        "pixego_result_ready", "pixego_message", "pixego_embed_password",
        "pixego_extract_password", "pixego_cover_upload", "pixego_stego_upload",
        "pixego_embed_mode", "pixego_embed_bits", "analysis_cover_upload",
        "analysis_stego_upload", "analysis_compare_upload",
    ):
        session_state.pop(key, None)