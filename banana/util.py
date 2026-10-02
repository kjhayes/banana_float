
import bitstring

def integer_to_bits(i: int, width: int):
    bits = bitstring.Bits(bin=bin(i))
    dropped_bits = width - bits.len
    if dropped_bits < 0:
        raise RuntimeError(f"Cannot convert integer {i} to bit representation of width {width}!")
    return bitstring.Bits(dropped_bits) + bits

