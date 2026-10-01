# Modelado LZSS: codificación y decodificación de tokens (Fase 1)
# lzss.py
from typing import List, Tuple, Union

WINDOW_SIZE = 4096
MIN_MATCH = 3
MAX_MATCH = 258

# Definición de tokens:
# LITERAL: ('L', valor_byte)
# MATCH:   ('M', offset, length)
Token = Union[Tuple[str, int], Tuple[str, int, int]]


def lzss_encode(data: bytes) -> List[Token]:
    tokens: List[Token] = []
    cursor = 0
    data_len = len(data)

    while cursor < data_len:
        # Definir los límites de la ventana de búsqueda deslizante
        win_start = max(0, cursor - WINDOW_SIZE)
        window = data[win_start:cursor]

        best_offset = 0
        best_length = 0

        # Longitud máxima posible que podemos contrastar
        max_possible_len = min(MAX_MATCH, data_len - cursor)

        # Buscamos coincidencias desde la longitud mínima hacia arriba
        if max_possible_len >= MIN_MATCH:
            # Optimizamos buscando prefijos directamente en la ventana
            for length in range(MIN_MATCH, max_possible_len + 1):
                candidate = data[cursor : cursor + length]
                pos = window.find(candidate)
                if pos != -1:
                    # offset = distancia hacia atrás desde la posición actual
                    best_offset = cursor - (win_start + pos)
                    best_length = length
                else:
                    # Si no encuentra un prefijo de tamaño k, no encontrará uno de k+1
                    break

        if best_length >= MIN_MATCH:
            tokens.append(('M', best_offset, best_length))
            cursor += best_length
        else:
            tokens.append(('L', data[cursor]))
            cursor += 1

    return tokens


def lzss_decode(tokens: List[Token]) -> bytes:
    output = bytearray()

    for token in tokens:
        tag = token[0]
        if tag == 'L':
            output.append(token[1])
        elif tag == 'M':
            offset = token[1]
            length = token[2]
            start = len(output) - offset
            for i in range(length):
                output.append(output[start + i])

    return bytes(output)