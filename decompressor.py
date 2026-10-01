import hashlib
import struct
from pathlib import Path
from typing import BinaryIO, Optional

from bitstream import BitReader
from compressor import MAGIC, DISTANCE_BITS
from huffman import (
    END_OF_BLOCK,
    FIRST_LENGTH_SYMBOL,
    HuffmanNode,
    build_huffman_tree,
    symbol_to_length,
)
from lzss import MIN_MATCH, MAX_MATCH


LAST_LENGTH_SYMBOL = FIRST_LENGTH_SYMBOL + MAX_MATCH - MIN_MATCH


def read_exact(file: BinaryIO, size: int) -> bytes:
    """Lee un campo completo o informa que el archivo está truncado."""
    data = file.read(size)

    if len(data) != size:
        raise EOFError("Cabecera incompleta")

    return data


def read_symbol(reader: BitReader, root: HuffmanNode) -> int:
    """Recorre el árbol hasta reconocer un símbolo."""
    node = root

    # Caso especial: un árbol con un único símbolo.
    # En la fase 3 le asignamos el código "0".
    if node.symbol is not None:
        if reader.read_bit() != 0:
            raise ValueError("Código inválido para un árbol de un símbolo")

        return node.symbol

    while node.symbol is None:
        bit = reader.read_bit()
        node = node.left if bit == 0 else node.right

        if node is None:
            raise ValueError("Código Huffman inválido")

    return node.symbol


def decompress_file(
    input_path: str,
    output_path: str,
    expected_sha256: Optional[str] = None,
) -> str:
    source = Path(input_path)
    destination = Path(output_path)

    if source.resolve() == destination.resolve():
        raise ValueError("La entrada y la salida deben ser distintas")

    with source.open("rb") as file:
        # 1. Leer la parte fija de la cabecera.
        header = read_exact(file, struct.calcsize(">4sQH"))

        magic, original_size, symbol_count = struct.unpack(
            ">4sQH", header
        )

        if magic != MAGIC:
            raise ValueError("Formato o versión de archivo no reconocidos")

        if not 1 <= symbol_count <= LAST_LENGTH_SYMBOL + 1:
            raise ValueError("Cantidad de símbolos inválida")

        # 2. Recuperar la tabla de frecuencias.
        frequencies = {}

        for _ in range(symbol_count):
            entry = read_exact(file, struct.calcsize(">HQ"))
            symbol, frequency = struct.unpack(">HQ", entry)

            if not 0 <= symbol <= LAST_LENGTH_SYMBOL:
                raise ValueError(f"Símbolo inválido: {symbol}")

            if frequency == 0 or symbol in frequencies:
                raise ValueError("Tabla de frecuencias inválida")

            frequencies[symbol] = frequency

        if frequencies.get(END_OF_BLOCK) != 1:
            raise ValueError("Falta un fin de flujo válido")

        # 3. Reconstruir el mismo árbol usado para comprimir.
        root = build_huffman_tree(frequencies)
        reader = BitReader(file)
        output = bytearray()

        # 4. Decodificar Huffman y reconstruir los bytes.
        while True:
            symbol = read_symbol(reader, root)

            if symbol == END_OF_BLOCK:
                break

            if 0 <= symbol <= 255:
                if len(output) >= original_size:
                    raise ValueError("La salida supera el tamaño original")

                output.append(symbol)

            else:
                length = symbol_to_length(symbol)

                # Se guardó distancia - 1: recuperamos sumando 1.
                distance = reader.read_bits(DISTANCE_BITS) + 1

                if distance > len(output):
                    raise ValueError("La referencia apunta fuera del historial")

                if len(output) + length > original_size:
                    raise ValueError("La salida supera el tamaño original")

                # Copiar byte a byte permite referencias superpuestas.
                for _ in range(length):
                    output.append(output[-distance])

        # Los bits restantes del último byte son relleno.
        if len(output) != original_size:
            raise ValueError("El tamaño recuperado no coincide con la cabecera")

    # 5. Calcular el hash y validarlo si se proporcionó el esperado.
    recovered_sha256 = hashlib.sha256(output).hexdigest()

    if expected_sha256 is not None:
        if recovered_sha256 != expected_sha256.strip().lower():
            raise ValueError("El SHA-256 no coincide con el original")

    # Escribir después de pasar las comprobaciones.
    destination.write_bytes(output)

    return recovered_sha256


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Descompresor LZSS + Huffman estático"
    )

    parser.add_argument("entrada", help="Archivo .lzh")
    parser.add_argument("salida", help="Archivo recuperado")

    parser.add_argument(
        "--original",
        help="Archivo original opcional para verificar el SHA-256",
    )

    args = parser.parse_args()

    expected_hash = None

    if args.original:
        expected_hash = hashlib.sha256(
            Path(args.original).read_bytes()
        ).hexdigest()

    recovered_hash = decompress_file(
        args.entrada,
        args.salida,
        expected_sha256=expected_hash,
    )

    print(f"Archivo recuperado: {args.salida}")
    print(f"SHA-256: {recovered_hash}")

    if expected_hash is not None:
        print("Verificación correcta: el SHA-256 coincide con el original")