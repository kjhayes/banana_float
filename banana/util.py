
import bitstring

def integer_to_bits(i: int, width: int|None):
    bits = bitstring.Bits(bin=bin(i))
    if width is None:
        return bits
    dropped_bits = width - bits.len
    if dropped_bits < 0:
        raise RuntimeError(f"Cannot convert integer {i} to bit representation of width {width}!")
    return bitstring.Bits(dropped_bits) + bits

