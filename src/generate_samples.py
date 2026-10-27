"""Membuat dua gambar cover sintetis (bertekstur dan area polos) ke folder sample_images."""
import os
import numpy as np
from PIL import Image, ImageDraw


def make_textured_cover(width=512, height=512, seed=7):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:height, 0:width]
    r = 128 + 90 * np.sin(x / 37.0) * np.cos(y / 53.0)
    g = 128 + 80 * np.sin((x + y) / 61.0)
    b = 128 + 70 * np.cos(x / 29.0 - y / 71.0)
    img = np.stack([r, g, b], axis=-1) + rng.normal(0, 6, (height, width, 3))
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def make_flat_cover(width=512, height=512):
    img = Image.new("RGB", (width, height), (30, 60, 120))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 220, 200], fill=(201, 40, 40))
    d.rectangle([260, 60, 470, 230], fill=(240, 240, 240))
    d.ellipse([80, 250, 260, 430], fill=(250, 200, 30))
    d.ellipse([300, 280, 440, 420], fill=(35, 160, 90))
    for i in range(0, width, 16):
        v = int(255 * i / width)
        d.rectangle([i, 450, i + 16, 500], fill=(v, 255 - v, 128))
    return img


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "sample_images")
    os.makedirs(out, exist_ok=True)
    make_textured_cover().save(os.path.join(out, "cover_tekstur.png"))
    make_flat_cover().save(os.path.join(out, "cover_polos.png"))
    print("Gambar contoh dibuat di", os.path.abspath(out))
