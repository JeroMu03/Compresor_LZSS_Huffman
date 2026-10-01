# Orquestador del pipeline completo (.bin final)
import struct
from pathlib import Path

from bitstream import BitWriter
from lzss import lzss_encode
from huffman import (
    END_OF_BLOCK,
    count_frequencies,
    build_huffman_tree,
    generate_huffman_codes,
    length_to_symbol,
)


MAGIC = b"LZH1"
DISTANCE_BITS = 12


def compress_file(input_path: str, output_path: str) -> None:
    source = Path(input_path)
    destination = Path(output_path)

    if source.resolve() == destination.resolve():
        raise ValueError("La entrada y la salida deben ser distintas")

    # Leer el archivo original como bytes.
    data = source.read_bytes()

    # Fase 1: generar tokens LZSS.
    tokens = lzss_encode(data)

    # Fase 2: contar frecuencias.
    frequencies = count_frequencies(tokens)

    # Fase 3: construir Huffman.
    root = build_huffman_tree(frequencies)
    codes = generate_huffman_codes(root)

    with destination.open("wb") as file:
        # Fase 4.1: escribir la cabecera.
        #
        # >  = orden de bytes big-endian
        # 4s = secuencia de 4 bytes
        # Q  = entero sin signo de 8 bytes
        # H  = entero sin signo de 2 bytes
        file.write(
            struct.pack(
                ">4sQH",
                MAGIC,
                len(data),
                len(frequencies),
            )
        )

        # Escribir la tabla de frecuencias.
        for symbol, frequency in sorted(frequencies.items()):
            file.write(
                struct.pack(">HQ", symbol, frequency)
            )

        # Fase 4.2: escribir el cuerpo como bits.
        writer = BitWriter(file)

        for token in tokens:
            if token[0] == "L":
                literal = token[1]
                writer.write_code(codes[literal])

            elif token[0] == "M":
                distance = token[1]
                length = token[2]

                # Primero, código Huffman de la longitud.
                symbol = length_to_symbol(length)
                writer.write_code(codes[symbol])

                # Después, distancia en 12 bits.
                # 1–4096 se representa mediante 0–4095.
                writer.write_bits(
                    distance - 1,
                    DISTANCE_BITS,
                )

            else:
                raise ValueError(f"Token desconocido: {token}")

        # Fase 4.3: indicar fin y completar el último byte.
        writer.write_code(codes[END_OF_BLOCK])
        writer.flush()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Compresor LZSS + Huffman estático"
    )

    parser.add_argument("entrada", help="Archivo original")
    parser.add_argument("salida", help="Archivo comprimido")

    args = parser.parse_args()

    compress_file(args.entrada, args.salida)

    original_size = Path(args.entrada).stat().st_size
    compressed_size = Path(args.salida).stat().st_size

    print(f"Tamaño original: {original_size} bytes")
    print(f"Tamaño comprimido: {compressed_size} bytes")

    if original_size > 0:
        saving = (1 - compressed_size / original_size) * 100
        print(f"Reducción: {saving:.2f}%")