# Lectura y escritura de bits individuales (Fase 4)
from typing import BinaryIO


class BitWriter:
    def __init__(self, file: BinaryIO):
        self.file = file
        self.buffer = 0
        self.bit_count = 0

    def write_bit(self, bit: int) -> None:
        """Agrega un bit al buffer."""
        if bit not in (0, 1):
            raise ValueError("El bit debe ser 0 o 1")

        self.buffer = (self.buffer << 1) | bit
        self.bit_count += 1

        # Cuando tenemos 8 bits, escribimos un byte.
        if self.bit_count == 8:
            self.file.write(bytes([self.buffer]))
            self.buffer = 0
            self.bit_count = 0
    

    def write_bits(self, value: int, width: int) -> None:
        """Escribe un entero usando una cantidad fija de bits."""
        if width < 0 or not 0 <= value < (1 << width):
            raise ValueError("El valor no entra en la cantidad de bits")

        # Escribimos desde el bit más significativo al menos significativo.
        for position in range(width - 1, -1, -1):
            bit = (value >> position) & 1
            self.write_bit(bit)

    def write_code(self, code: str) -> None:
        """Escribe un código Huffman, por ejemplo '110'."""
        for bit in code:
            if bit not in ("0", "1"):
                raise ValueError("Código binario inválido")

            self.write_bit(int(bit))

    def flush(self) -> None:
        """Completa el último byte con ceros a la derecha."""
        if self.bit_count > 0:
            padding = 8 - self.bit_count
            self.buffer <<= padding

            self.file.write(bytes([self.buffer]))

            self.buffer = 0
            self.bit_count = 0



class BitReader:
    def __init__(self, file: BinaryIO):
        self.file = file
        self.buffer = 0
        self.bits_remaining = 0

    def read_bit(self) -> int:
        """Lee un bit, desde el más significativo al menos significativo."""
        if self.bits_remaining == 0:
            byte = self.file.read(1)

            if not byte:
                raise EOFError("El archivo terminó antes del fin de flujo")

            self.buffer = byte[0]
            self.bits_remaining = 8

        self.bits_remaining -= 1

        return (self.buffer >> self.bits_remaining) & 1

    def read_bits(self, width: int) -> int:
        """Lee una cantidad fija de bits y devuelve su valor entero."""
        value = 0

        for _ in range(width):
            value = (value << 1) | self.read_bit()

        return value