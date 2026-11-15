"""Sistem pakar kesiapsiagaan banjir dan tanah longsor (Forward Chaining).

Mode tanya jawab : python sistem_pakar.py
Mode cepat       : python sistem_pakar.py --fakta 1,3,5
                   (angka = nomor fakta pada daftar pertanyaan, atau tulis nama faktanya)
"""
import argparse
import json
import os

MODE_VALID = ("dan", "atau")
KB_BAWAAN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kb_banjir_longsor.json")


# ---------------------------------------------------------------- basis aturan
def muat_kb(path):
    with open(path, encoding="utf-8") as f:
        kb = json.load(f)
    periksa_kb(kb)
    return kb


def periksa_kb(kb):
    """Pemeriksaan kualitas dasar: id unik, mode sah, sumber terdaftar, kesimpulan ada."""
    ids = set()
    for r in kb["aturan"]:
        if r["id"] in ids:
            raise ValueError(f"id aturan ganda: {r['id']}")
        ids.add(r["id"])
        if r["mode"] not in MODE_VALID:
            raise ValueError(f"{r['id']}: mode harus 'dan' atau 'atau'")
        if not r["jika"]:
            raise ValueError(f"{r['id']}: daftar 'jika' kosong")
        for s in r["sumber"]:
            if s not in kb["sumber"]:
                raise ValueError(f"{r['id']}: sumber {s} tidak terdaftar")
    hasil = {r["maka"] for r in kb["aturan"]}
    for k in kb["kesimpulan"]:
        if k not in hasil:
            raise ValueError(f"kesimpulan '{k}' tidak dihasilkan aturan mana pun")


def fakta_dasar(kb):
    """Fakta yang tidak pernah menjadi hasil aturan: inilah yang ditanyakan ke user."""
    hasil = {r["maka"] for r in kb["aturan"]}
    dasar = []
    for r in kb["aturan"]:
        for j in r["jika"]:
            if j not in hasil and j not in dasar:
                dasar.append(j)
    return dasar


# --------------------------------------------------------------- mesin inferensi
def syarat_terpenuhi(aturan, memori):
    cek = (j in memori for j in aturan["jika"])
    return any(cek) if aturan["mode"] == "atau" else all(cek)


def forward_chaining(kb, fakta_awal):
    """Cocokkan -> eksekusi satu aturan -> perbarui memori, sampai tidak ada aturan baru.

    Aturan yang hasilnya sudah ada di memori dilewati (refraction), jadi pasti berhenti.
    """
    memori = set(fakta_awal)
    asal = {}      # fakta turunan -> aturan penghasilnya (bahan penjelasan)
    log = []
    siklus = 0
    while True:
        siklus += 1
        konflik = [r for r in kb["aturan"]
                   if r["maka"] not in memori and syarat_terpenuhi(r, memori)]
        if not konflik:
            log.append(f"Siklus {siklus}: tidak ada aturan baru, berhenti")
            return memori, asal, log
        r = konflik[0]   # conflict resolution: aturan dengan urutan paling awal
        memori.add(r["maka"])
        asal[r["maka"]] = r
        log.append(f"Siklus {siklus}: {r['id']} -> {r['maka']}")


def syarat_dipakai(aturan, memori):
    return [j for j in aturan["jika"] if j in memori]


def pilih_kesimpulan(kb, memori):
    """Dari kesimpulan yang tercapai, ambil level tertinggi untuk tiap jenis bencana."""
    terbaik = {}
    for nama, info in kb["kesimpulan"].items():
        if nama not in memori:
            continue
        lama = terbaik.get(info["jenis"])
        if lama is None or info["tingkat"] > kb["kesimpulan"][lama]["tingkat"]:
            terbaik[info["jenis"]] = nama
    return list(terbaik.values())


def jelaskan(fakta, asal, memori, kedalaman=1):
    """Fasilitas penjelasan 'Bagaimana': telusuri mundur sampai fakta dari user."""
    r = asal[fakta]
    pakai = syarat_dipakai(r, memori)
    print("  " * kedalaman + f"{fakta}  <- {r['id']} [{', '.join(r['sumber'])}] ({', '.join(pakai)})")
    for j in pakai:
        if j in asal:
            jelaskan(j, asal, memori, kedalaman + 1)


# --------------------------------------------------------------------- masukan
def tanya_user(dasar):
    print("Jawab y/t.")
    ya = []
    for i, f in enumerate(dasar, 1):
        while True:
            jawab = input(f"{i}. Apakah {f}? (y/t) > ").strip().lower()
            if jawab in ("y", "t"):
                break
        if jawab == "y":
            ya.append(f)
    return ya


def baca_fakta_cli(teks, dasar):
    """Terima nomor (1,3,5) atau nama fakta, dipisah koma. Kembalikan (fakta, tak_dikenal)."""
    ya, asing = [], []
    for token in (t.strip() for t in teks.split(",")):
        if not token:
            continue
        if token.isdigit() and 1 <= int(token) <= len(dasar):
            ya.append(dasar[int(token) - 1])
        elif token in dasar:
            ya.append(token)
        else:
            asing.append(token)
    return ya, asing


# ------------------------------------------------------------------------ utama
def main():
    ap = argparse.ArgumentParser(description="Sistem pakar banjir dan longsor (forward chaining)")
    ap.add_argument("--kb", default=KB_BAWAAN, help="file aturan (JSON)")
    ap.add_argument("--fakta", help="fakta 'ya' (nomor atau nama, dipisah koma), tanpa tanya jawab")
    a = ap.parse_args()

    kb = muat_kb(a.kb)
    dasar = fakta_dasar(kb)
    print(kb["judul"])

    if a.fakta is not None:
        ya, asing = baca_fakta_cli(a.fakta, dasar)
        if asing:
            print("Fakta tidak dikenal:", "; ".join(asing))
            print("Fakta yang tersedia:")
            for i, f in enumerate(dasar, 1):
                print(f"  {i}. {f}")
            return
    else:
        ya = tanya_user(dasar)

    print("\nFakta awal:", ", ".join(ya) if ya else "(tidak ada)")
    print()
    memori, asal, log = forward_chaining(kb, ya)
    for baris in log:
        print(baris)

    akhir = pilih_kesimpulan(kb, memori)
    print()
    if not akhir:
        print("Kesimpulan: tidak ada level peringatan yang dapat ditetapkan dari fakta tersebut.")
        print("Tetap pantau informasi resmi BPBD, BMKG, atau PVMBG.")
    else:
        print("Kesimpulan:")
        for k in akhir:
            print(f"- {k.upper()}")
            print(f"  {kb['saran'][k]}")
        print("\nAlasan:")
        for k in akhir:
            jelaskan(k, asal, memori)

    print("\nCatatan:", kb["batas"])


if __name__ == "__main__":
    main()