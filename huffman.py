# Árbol, cálculo de frecuencias y códigos (Fases 2 y 3)
import heapq
from collections import Counter
from typing import Dict, List
from itertools import count
from dataclasses import dataclass
from typing import Optional

from lzss import Token, MIN_MATCH, MAX_MATCH

END_OF_BLOCK = 256
FIRST_LENGTH_SYMBOL = 257


def length_to_symbol(length: int) -> int:
    """Convierte una longitud de coincidencia en un símbolo."""
    if not MIN_MATCH <= length <= MAX_MATCH:
        raise ValueError(f"Longitud fuera de rango: {length}")

    return FIRST_LENGTH_SYMBOL + (length - MIN_MATCH)


def symbol_to_length(symbol: int) -> int:
    """Recupera la longitud representada por un símbolo."""
    length = MIN_MATCH + (symbol - FIRST_LENGTH_SYMBOL)

    if not MIN_MATCH <= length <= MAX_MATCH:
        raise ValueError(f"Símbolo de longitud inválido: {symbol}")

    return length


def count_frequencies(tokens: List[Token]) -> Dict[int, int]:
    """Cuenta los símbolos que posteriormente codificará Huffman."""
    frequencies = Counter()

    for token in tokens:
        if token[0] == "L":
            # El símbolo de un literal es su propio valor de byte.
            symbol = token[1]

        elif token[0] == "M":
            # MATCH = ('M', distancia, longitud).
            symbol = length_to_symbol(token[2])

        else:
            raise ValueError(f"Token desconocido: {token}")

        frequencies[symbol] += 1

    # Siempre se emitirá un fin de flujo, incluso para un archivo vacío.
    frequencies[END_OF_BLOCK] += 1

    return dict(frequencies)


@dataclass
class HuffmanNode:
    # Las hojas tienen un símbolo.
    # Los nodos internos tienen hijos y symbol=None.
    symbol: Optional[int] = None
    left: Optional["HuffmanNode"] = None
    right: Optional["HuffmanNode"] = None


def build_huffman_tree(
    frequencies: Dict[int, int]
) -> HuffmanNode:
    """Construye el árbol uniendo los nodos menos frecuentes."""
    if not frequencies:
        raise ValueError("La tabla de frecuencias está vacía")

    heap = []
    tie_breaker = count()

    # Crear una hoja por símbolo.
    for symbol, frequency in sorted(frequencies.items()):
        if frequency <= 0:
            raise ValueError("Las frecuencias deben ser positivas")

        node = HuffmanNode(symbol=symbol)

        heapq.heappush(
            heap,
            (frequency, next(tie_breaker), node)
        )

    # Unir los dos nodos menos frecuentes hasta tener una raíz.
    while len(heap) > 1:
        frequency_left, _, left = heapq.heappop(heap)
        frequency_right, _, right = heapq.heappop(heap)

        parent = HuffmanNode(left=left, right=right)

        heapq.heappush(
            heap,
            (
                frequency_left + frequency_right,
                next(tie_breaker),
                parent
            )
        )

    return heap[0][2]


def generate_huffman_codes(
    root: HuffmanNode
) -> Dict[int, str]:
    """Recorre el árbol y asigna un código a cada símbolo."""
    codes = {}

    def traverse(node: HuffmanNode, prefix: str) -> None:
        if node.symbol is not None:
            # Si existe un único símbolo, darle el código "0".
            codes[node.symbol] = prefix or "0"
            return

        if node.left is not None:
            traverse(node.left, prefix + "0")

        if node.right is not None:
            traverse(node.right, prefix + "1")

    traverse(root, "")
    return codes

if __name__ == "__main__":
    from lzss import lzss_encode

    data = b"ABCABCABC"

    # Fase 1: generar tokens.
    tokens = lzss_encode(data)

    # Fase 2: contar frecuencias.
    frequencies = count_frequencies(tokens)

    # Fase 3: construir el árbol y generar códigos.
    root = build_huffman_tree(frequencies)
    codes = generate_huffman_codes(root)

    print("Tokens:", tokens)
    print("Frecuencias:", frequencies)

    print("\nCódigos Huffman:")
    for symbol, code in sorted(codes.items()):
        print(f"Símbolo {symbol}: {code}")