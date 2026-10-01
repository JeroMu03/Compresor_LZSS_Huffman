# Script para validar con el corpus y comprobar SHA-256from lzss import lzss_encode, lzss_decode

from lzss import lzss_encode, lzss_decode
import hashlib
import os
import unittest

DIRECTORIO_BASE = os.path.dirname(os.path.abspath(__file__))
CARPETA_PRUEBAS = os.path.join(DIRECTORIO_BASE, "pruebas")

# Hashes extraidos de README_pruebas.txt
HASHES_ESPERADOS = {
    "prueba_1_pequena.txt": "8a0d7e04cc6347ca94cf03f7329ad7bf5881bfaff6d26da42e86166822c20051",
    "prueba_2_texto_natural.txt": "410d0deaf3cdfd3a51595d084445727ccc1c2c154b910738e0e32934bbbae403",
    "prueba_3_alta_repeticion.txt": "a54f4a85a8695e1bec7cf49603301d97bd08c89f98dddb09fb0605fa1f88e36e",
    "prueba_4_baja_repeticion.txt": "7b7b0ac6050531d99b338e2db14c188565bbf12f4b08a97b4398b7eda28b6d61",
}


def calcular_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TestCorpusIntegridad(unittest.TestCase):
    """Valida que los archivos de prueba en disco coincidan con los hashes originales."""
    def test_verificar_archivos_corpus(self):
        for nombre, sha_esperado in HASHES_ESPERADOS.items():
            ruta_archivo = os.path.join(CARPETA_PRUEBAS, nombre)

            self.assertTrue(
                os.path.exists(ruta_archivo),
                f"No se encontró el archivo '{nombre}' en la ruta: {ruta_archivo}",
            )
            with open(ruta_archivo, "rb") as f:
                contenido = f.read()

            sha_calculado = calcular_sha256(contenido)
            self.assertEqual(
                sha_calculado,
                sha_esperado,
                f"El archivo {nombre} no coincide con el SHA-256 provisto.",
            )


class TestLZSS(unittest.TestCase):
    """Pruebas unitarias exclusivas de la Fase 1 (LZSS)."""

    def test_muestra_sintetica(self):
        muestra = b"BANANA BANANA BANANA"
        tokens = lzss_encode(muestra)
        reconstruido = lzss_decode(tokens)
        self.assertEqual(muestra, reconstruido)

    def test_reversibilidad_corpus(self):
        for nombre in HASHES_ESPERADOS:
            ruta_archivo = os.path.join(CARPETA_PRUEBAS, nombre)

            self.assertTrue(
                os.path.exists(ruta_archivo),
                f"No se encontró el archivo '{nombre}' en: {ruta_archivo}",
            )
            with open(ruta_archivo, "rb") as f:
                original = f.read()

            tokens = lzss_encode(original)
            reconstruido = lzss_decode(tokens)

            self.assertEqual(
                original,
                reconstruido,
                f"Fallo de reversibilidad LZSS en {nombre}",
            )

# class TestHuffman(unittest.TestCase): ...
# class TestBitStream(unittest.TestCase): ...
# class TestCompresorEndToEnd(unittest.TestCase): ...

if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    # --- Comenta / Descomenta según lo que quieras ejecutar ---
    # Para cargar una clase entera:
    suite.addTests(loader.loadTestsFromTestCase(TestCorpusIntegridad))
    suite.addTests(loader.loadTestsFromTestCase(TestLZSS))
    # suite.addTests(loader.loadTestsFromTestCase(TestHuffman))

    # Para cargar un solo método puntual:
    # suite.addTest(TestLZSS('test_muestra_sintetica'))

    # Ejecutar la suite configurada
    runner.run(suite)