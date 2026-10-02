import csv
import gzip
import hashlib
import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

# Importación directa de tus módulos
from compressor import compress_file
from decompressor import decompress_file

BASE_DIR = Path(__file__).parent
CORPUS_DIR = BASE_DIR / "Corpus_Pruebas_Compresion_TDI"
OUTPUT_DIR = BASE_DIR / "results" / "temp_benchmark"
RESULTS_DIR = BASE_DIR / "results"

# Hashes oficiales de la cátedra
EXPECTED_DATA = {
    "prueba_1_pequena.txt": {
        "sha256": "8a0d7e04cc6347ca94cf03f7329ad7bf5881bfaff6d26da42e86166822c20051",
        "size": 64,
    },
    "prueba_2_texto_natural.txt": {
        "sha256": "410d0deaf3cdfd3a51595d084445727ccc1c2c154b910738e0e32934bbbae403",
        "size": 102400,
    },
    "prueba_3_alta_repeticion.txt": {
        "sha256": "a54f4a85a8695e1bec7cf49603301d97bd08c89f98dddb09fb0605fa1f88e36e",
        "size": 102400,
    },
    "prueba_4_baja_repeticion.txt": {
        "sha256": "7b7b0ac6050531d99b338e2db14c188565bbf12f4b08a97b4398b7eda28b6d61",
        "size": 102400,
    },
}


def calcular_sha256(ruta_archivo: Path) -> str:
    hasher = hashlib.sha256()
    with open(ruta_archivo, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def comprimir_gzip_baseline(archivo_in: Path, archivo_out: Path):
    """Gzip nivel 6 sin metadatos (gzip -n -6)"""
    with open(archivo_in, "rb") as f_in:
        data = f_in.read()
    with open(archivo_out, "wb") as f_out:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=f_out, compresslevel=6, mtime=0
        ) as gz:
            gz.write(data)


def obtener_binario_zpaq() -> str:
    """Busca el ejecutable de ZPAQ en la carpeta zpaq715 o en la raíz."""
    posibles_rutas = [
        BASE_DIR / "zpaq715" / "zpaq64.exe",
        BASE_DIR / "zpaq715" / "zpaq.exe",
        BASE_DIR / "zpaq.exe",
    ]
    for ruta in posibles_rutas:
        if ruta.exists():
            return str(ruta)
    return "zpaq"  # Intenta usar el PATH si no está localmente


def comprimir_zpaq(archivo_in: Path, archivo_out: Path) -> float:
    """Comprime usando el binario oficial de ZPAQ y mide el tiempo en ms."""
    if archivo_out.exists():
        archivo_out.unlink()

    zpaq_bin = obtener_binario_zpaq()

    # Comando estándar de ZPAQ: 'a' (add/archive) sin cifrado
    comando = [zpaq_bin, "a", str(archivo_out), str(archivo_in)]

    t0 = time.perf_counter()
    subprocess.run(
        comando,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    t1 = time.perf_counter()

    return (t1 - t0) * 1000

def calcular_weissman(
    r_propio: float, r_ref: float, t_propio_ms: float, t_ref_ms: float
) -> float:
    try:
        t_ms = max(t_propio_ms, 1.01)
        t_ref = max(t_ref_ms, 1.01)
        w = 1.0 * (r_propio / r_ref) * (math.log(t_ref) / math.log(t_ms))
        return round(w, 4)
    except Exception:
        return 0.0


def run_benchmark():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Verificar disponibilidad de ZPAQ
    has_zpaq = (
        shutil.which("zpaq") is not None
        or (BASE_DIR / "zpaq715" / "zpaq64.exe").exists()
        or (BASE_DIR / "zpaq715" / "zpaq.exe").exists()
        or (BASE_DIR / "zpaq.exe").exists()
    )
    if not has_zpaq:
        print(
            "⚠️ AVISO: 'zpaq' no está en el PATH ni en la raíz como zpaq.exe. "
            "Se omitirá la corrida real de ZPAQ."
        )

    print("=" * 128)
    print(" " * 42 + "BENCHMARK DE COMPRESIÓN - TDI 2026")
    print(" " * 32 + "Propio (LZSS+Huffman) vs Mercado (ZPAQ) vs Baseline (Gzip-6)")
    print("=" * 128)

    filas_reporte = []

    for archivo_nombre, meta in EXPECTED_DATA.items():
        ruta_orig = CORPUS_DIR / archivo_nombre

        if not ruta_orig.exists():
            print(f"[ALERTA] Archivo no encontrado: {ruta_orig}")
            continue

        tam_orig = ruta_orig.stat().st_size
        sha_orig_real = calcular_sha256(ruta_orig)

        # --- 1. Propio: LZSS + Huffman ---
        ruta_lzh = OUTPUT_DIR / f"{archivo_nombre}.lzh"
        t0 = time.perf_counter()
        compress_file(str(ruta_orig), str(ruta_lzh))
        t1 = time.perf_counter()
        t_comp_propio_ms = (t1 - t0) * 1000

        tam_comp_propio = ruta_lzh.stat().st_size
        ratio_propio = tam_orig / tam_comp_propio if tam_comp_propio else 0

        # Verificación SHA-256
        ruta_rec = OUTPUT_DIR / f"rec_{archivo_nombre}"
        decompress_file(str(ruta_lzh), str(ruta_rec))
        rec_hash = calcular_sha256(ruta_rec)
        sha_ok = (
            rec_hash.lower() == meta["sha256"].lower()
            and sha_orig_real.lower() == meta["sha256"].lower()
        )

        # --- 2. Baseline de Cátedra: Gzip -6 ---
        ruta_gz = OUTPUT_DIR / f"{archivo_nombre}.gz"
        t4 = time.perf_counter()
        comprimir_gzip_baseline(ruta_orig, ruta_gz)
        t5 = time.perf_counter()
        t_comp_gz_ms = (t5 - t4) * 1000

        tam_comp_gz = ruta_gz.stat().st_size
        ratio_gz = tam_orig / tam_comp_gz if tam_comp_gz else 0

        # --- 3. Mercado Asignado: ZPAQ ---
        ruta_zpaq = OUTPUT_DIR / f"{archivo_nombre}.zpaq"
        t_comp_zpaq_ms = 0.0
        tam_comp_zpaq = 0
        ratio_zpaq = 0.0
        w_score_zpaq = 0.0

        if has_zpaq:
            try:
                t_comp_zpaq_ms = comprimir_zpaq(ruta_orig, ruta_zpaq)
                tam_comp_zpaq = ruta_zpaq.stat().st_size
                ratio_zpaq = (
                    tam_orig / tam_comp_zpaq if tam_comp_zpaq else 0
                )
                w_score_zpaq = calcular_weissman(
                    ratio_zpaq, ratio_gz, t_comp_zpaq_ms, t_comp_gz_ms
                )
            except Exception as e:
                print(f"[ERROR ZPAQ en {archivo_nombre}]: {e}")

        # Weissman Score solución propia
        w_score_propio = calcular_weissman(
            ratio_propio, ratio_gz, t_comp_propio_ms, t_comp_gz_ms
        )

        filas_reporte.append(
            {
                "Archivo": archivo_nombre,
                "Orig (B)": tam_orig,
                "LZ+Huff (B)": tam_comp_propio,
                "Ratio Propio": round(ratio_propio, 2),
                "T.Propio (ms)": round(t_comp_propio_ms, 2),
                "W.Propio": w_score_propio,
                "ZPAQ (B)": tam_comp_zpaq,
                "Ratio ZPAQ": round(ratio_zpaq, 2),
                "T.ZPAQ (ms)": round(t_comp_zpaq_ms, 2),
                "W.ZPAQ": w_score_zpaq,
                "Gzip (B)": tam_comp_gz,
                "Ratio Gzip": round(ratio_gz, 2),
                "T.Gzip (ms)": round(t_comp_gz_ms, 2),
                "SHA256 Match": "OK" if sha_ok else "FALLÓ",
            }
        )

    # Imprimir cuadro comparativo
    header = (
        f"{'Archivo':<26} | {'Orig':<6} | {'R.Prop':<6} | {'T.Prop(ms)':<10} | {'W.Prop':<6} | "
        f"{'R.ZPAQ':<6} | {'T.ZPAQ(ms)':<10} | {'W.ZPAQ':<6} | "
        f"{'R.Gzip':<6} | {'T.Gzip(ms)':<10} | {'SHA':<4}"
    )
    print(header)
    print("-" * len(header))

    for f in filas_reporte:
        print(
            f"{f['Archivo']:<26} | "
            f"{f['Orig (B)']:<6} | "
            f"{f['Ratio Propio']:<6.2f} | "
            f"{f['T.Propio (ms)']:<10.1f} | "
            f"{f['W.Propio']:<6.3f} | "
            f"{f['Ratio ZPAQ']:<6.2f} | "
            f"{f['T.ZPAQ (ms)']:<10.1f} | "
            f"{f['W.ZPAQ']:<6.3f} | "
            f"{f['Ratio Gzip']:<6.2f} | "
            f"{f['T.Gzip (ms)']:<10.1f} | "
            f"{f['SHA256 Match']:<4}"
        )
    print("=" * 128)

    # Guardar CSV
    csv_file = RESULTS_DIR / "benchmark_comparativo_zpaq.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(filas_reporte[0].keys()))
        writer.writeheader()
        writer.writerows(filas_reporte)

    # Guardar JSON
    json_file = RESULTS_DIR / "benchmark_comparativo_zpaq.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(filas_reporte, f, indent=4)

    print(f"\n[+] Tabla comparativa completa guardada en:")
    print(f"    - {csv_file}")
    print(f"    - {json_file}")


if __name__ == "__main__":
    run_benchmark()