"""
Pixego: antarmuka baris perintah untuk steganografi LSB + AES-256-GCM.

Contoh:
  python cli.py kapasitas ../sample_images/cover_tekstur.png
  python cli.py embed -i ../sample_images/cover_tekstur.png -o stego.png -m "pesan rahasia"
  python cli.py embed -i foto_hp.jpg -o stego.png -m "halo" --max-side 1024 --save-cover cover_kecil.png
  python cli.py extract -i stego.png
  python cli.py metrik cover_kecil.png stego.png
  python cli.py chi-square stego.png

Catatan penting:
  Cover dibuka dengan load_cover (rotasi EXIF diterapkan, transparansi diratakan, bisa diperkecil).
  Stego image TIDAK boleh diproses seperti itu, jadi extract dan chi-square membukanya apa adanya.
"""
import argparse
import getpass
import os
import sys

from PIL import Image

import stego_core as sc

FORMAT_OUTPUT_AMAN = (".png", ".bmp")


def ambil_password(args):
    if args.password:
        return args.password
    return getpass.getpass("Password: ")


def buka_stego(path):
    """Stego dibuka apa adanya (tanpa rotasi EXIF atau resize) agar urutan piksel tidak berubah."""
    try:
        return Image.open(path).convert("RGB")
    except Exception as e:
        raise sc.StegoError(f"Gambar tidak bisa dibuka ({type(e).__name__}).") from None


def cmd_kapasitas(args):
    img = sc.load_cover(args.gambar, max_side=args.max_side)
    print(f"Ukuran gambar (setelah dimuat): {img.size[0]} x {img.size[1]}")
    for k in (1, 2, 3):
        print(f"  {k} bit per kanal : {sc.capacity_bytes(img.size, k)} byte")


def cmd_embed(args):
    ext = os.path.splitext(args.output)[1].lower()
    if ext not in FORMAT_OUTPUT_AMAN:
        print("GAGAL: file output harus .png atau .bmp (lossless). "
              "JPG dan WebP mengubah nilai piksel sehingga pesan hilang.", file=sys.stderr)
        return 2

    if args.message_file:
        with open(args.message_file, "rb") as f:
            pesan = f.read()
    elif args.message is not None:
        pesan = args.message.encode("utf-8")
    else:
        print("Isi pesan dengan -m atau --message-file", file=sys.stderr)
        return 2

    cover = sc.load_cover(args.input, max_side=args.max_side)
    password = ambil_password(args)
    stego, info = sc.embed(cover, pesan, password, mode=args.mode, bits=args.bits)
    stego.save(args.output)
    print("Berhasil disimpan ke", args.output)
    for k, v in info.items():
        print(f"  {k}: {v}")
    print(f"  MSE : {sc.mse(cover, stego):.6f}  (dibanding cover yang sudah dimuat)")
    print(f"  PSNR: {sc.psnr(cover, stego):.2f} dB")

    if args.save_cover:
        cover.save(args.save_cover)
        print("Cover yang sudah dimuat disimpan ke", args.save_cover,
              "(pakai ini sebagai pembanding untuk perintah metrik)")

    if not args.tanpa_verifikasi:
        hasil = sc.extract(buka_stego(args.output), password)
        if hasil != pesan:
            raise sc.StegoError("Verifikasi gagal: pesan dari file hasil tidak sama dengan aslinya.")
        print("Verifikasi: pesan berhasil dibaca ulang dari file hasil.")
    return 0


def cmd_extract(args):
    data = sc.extract(buka_stego(args.input), ambil_password(args))
    if args.output:
        with open(args.output, "wb") as f:
            f.write(data)
        print("Pesan disimpan ke", args.output)
    else:
        try:
            print(data.decode("utf-8"))
        except UnicodeDecodeError:
            print(f"(Data biner {len(data)} byte, gunakan -o untuk menyimpan ke file)")
    return 0


def cmd_metrik(args):
    a = sc.load_cover(args.asli, max_side=args.max_side)
    b = buka_stego(args.stego)
    if a.size != b.size:
        print(f"Ukuran berbeda: asli {a.size}, stego {b.size}. "
              "Kalau embed memakai --max-side, gunakan file dari --save-cover sebagai gambar asli.",
              file=sys.stderr)
        return 2
    print(f"MSE : {sc.mse(a, b):.6f}")
    print(f"PSNR: {sc.psnr(a, b):.2f} dB")
    return 0


def cmd_chi(args):
    p = sc.chi_square_full(buka_stego(args.gambar))
    print(f"p-value chi-square seluruh gambar: {p:.4f}")
    print("Dekat 1 = dicurigai ada data tersembunyi. Dekat 0 = dianggap bersih.")
    print("Catatan: hasil bergantung pada karakter gambar, bandingkan dengan cover asli.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Pixego: steganografi LSB + AES-256-GCM")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("kapasitas", help="Hitung kapasitas pesan")
    s.add_argument("gambar")
    s.add_argument("--max-side", type=int, help="Perkecil sisi terpanjang ke nilai ini")
    s.set_defaults(fn=cmd_kapasitas)

    s = sub.add_parser("embed", help="Enkripsi dan sisipkan pesan")
    s.add_argument("-i", "--input", required=True, help="Gambar cover (PNG, JPG, BMP, WebP, dan lainnya)")
    s.add_argument("-o", "--output", required=True, help="Stego image (.png atau .bmp)")
    s.add_argument("-m", "--message", help="Teks pesan")
    s.add_argument("--message-file", help="File berisi pesan (boleh biner)")
    s.add_argument("--mode", choices=["random", "sequential"], default="random")
    s.add_argument("--bits", type=int, choices=[1, 2, 3], default=1)
    s.add_argument("--max-side", type=int, help="Perkecil cover ke sisi terpanjang ini sebelum disisipi")
    s.add_argument("--save-cover", help="Simpan cover yang sudah dimuat (untuk pembanding metrik)")
    s.add_argument("--tanpa-verifikasi", action="store_true",
                   help="Lewati pembacaan ulang file hasil (lebih cepat, kurang aman)")
    s.add_argument("-p", "--password", help="Kalau kosong, akan ditanya (lebih aman)")
    s.set_defaults(fn=cmd_embed)

    s = sub.add_parser("extract", help="Ekstrak dan dekripsi pesan")
    s.add_argument("-i", "--input", required=True, help="Stego image")
    s.add_argument("-o", "--output", help="Simpan hasil ke file")
    s.add_argument("-p", "--password")
    s.set_defaults(fn=cmd_extract)

    s = sub.add_parser("metrik", help="Hitung MSE dan PSNR")
    s.add_argument("asli")
    s.add_argument("stego")
    s.add_argument("--max-side", type=int, help="Sama dengan nilai yang dipakai saat embed")
    s.set_defaults(fn=cmd_metrik)

    s = sub.add_parser("chi-square", help="Uji chi-square seluruh gambar")
    s.add_argument("gambar")
    s.set_defaults(fn=cmd_chi)

    args = ap.parse_args()
    try:
        sys.exit(args.fn(args) or 0)
    except sc.StegoError as e:
        print("GAGAL:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
