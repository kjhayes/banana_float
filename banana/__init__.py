
import bitstring
from abc import ABC,abstractmethod

# Representation of a floating point value
# with unlimited bits available for the mantissa
# and exponent.
#
# Any operation which cannot be done without
# rounding should raise an exception.
# (e.g. division which causes repeated binary digits).
class PreciseFPValue:

    def __init__(self, base: int, exp: int):
        while base != 0 and base % 2 == 0:
            base = base // 2
            exp = exp + 1
        self.base = base
        self.exp = exp

    @classmethod
    def from_ieee754_bits(cls, sign: bool, exp_data, mant_data):

        exp_bits = exp_data.len
        bias = (2**(exp_bits-1))-1

        popcount = exp_data.count(1)
        if popcount == exp_bits:
            raise RuntimeError("Cannot encode NaN/Inf as PreciseFPValue!")

        subnormal = popcount == 0

        biased_exp = exp_data.uint
        unbiased_exp = biased_exp - bias

        unbiased_exp += 1
        if not subnormal:
            mant_data = mant_data.copy()
            mant_data.prepend('0b1')

        unbiased_exp -= mant_data.len
        mant_integer = mant_data.uint

        if sign:
            base = -mant_integer
        else:
            base = mant_integer

        return cls(base, unbiased_exp)

    @classmethod
    def from_integer(cls, value: int):
        return cls(value, 0)

    @classmethod
    def from_f64(cls, value):
        bits = bitstring.BitArray(f"float64={value}")
        sign = bits[0:1] == '0b1'
        exp_data = bits[1:12] 
        mant_data = bits[12:64]
        return cls.from_ieee754_bits(sign, exp_data, mant_data)

    @classmethod
    def from_f32(cls, value):
        bits = bitstring.BitArray(f"float32={value}")
        sign = bits[0:1] == '0b1'
        exp_data = bits[1:9] 
        mant_data = bits[9:32]
        return cls.from_ieee754_bits(sign, exp_data, mant_data)

    def approx_value(self):
        return self.base * 2**self.exp

    def __repr__(self):
        return f"[{self.approx_value()} = {self.base}*2^{self.exp}]"

    @classmethod
    def scale_pair(cls, left, right):
        assert(isinstance(left, PreciseFPValue))
        assert(isinstance(right, PreciseFPValue))
        l_base = left.base
        r_base = right.base
        if left.exp < right.exp:
            diff = right.exp - left.exp
            exp = left.exp
            r_base *= 2**diff
        else: 
            diff = left.exp - right.exp
            exp = right.exp
            l_base *= 2**diff
        return l_base, r_base, exp

    @classmethod
    def coerce(cls, other):
        if isinstance(other, PreciseFPValue):
            return other
        elif isinstance(other, FPValue):
            return other.to_precise()
        elif isinstance(other, int):
            return PreciseFPValue(other, 0)
        elif isinstance(other, float):
            return PreciseFPValue.from_f64(other)
        raise RuntimeError("Cannot coerce object of type {type(other)} to PreciseFPValue!")

    def __add__(self, other):
        other = PreciseFPValue.coerce(other)
        s_base, o_base, exp = PreciseFPValue.scale_pair(self,other)
        return PreciseFPValue(s_base + o_base, exp)

    def __sub__(self, other):
        other = PreciseFPValue.coerce(other)
        s_base, o_base, exp = PreciseFPValue.scale_pair(self,other)
        return PreciseFPValue(s_base - o_base, exp)

    def __mul__(self, other):
        other = PreciseFPValue.coerce(other)
        base = self.base * other.base
        exp = self.exp + other.exp
        return PreciseFPValue(base, exp)

    def __eq__(self, other):
        other = PreciseFPValue.coerce(other)
        return self.base == other.base and self.exp == other.exp

    def __lt__(self, other):
        other = PreciseFPValue.coerce(other)
        s_base, o_base, _ = PreciseFPValue.scale_pair(self, other)
        return s_base < o_base

    def __truediv__(self, other):
        other = PreciseFPValue.coerce(other)
        if self.base % other.base == 0:
            return PreciseFPValue(self.base // other.base, self.exp - other.exp)
        raise RuntimeError(f"Cannot divide PreciseFPValue {self} by {other} without rounding!")

    def to_normal_imprecise(self):
        sign = self.base < 0
        base = abs(self.base)
        if base == 0:
            return FPValue(False, bitstring.Bits('0b0'), bitstring.Bits('0b0'))
        exp = self.exp

        mant_data = bitstring.BitArray(bin=bin(base))

        # Drop any leading zeros
        while mant_data[0:1] == '0b0':
            del mant_data[0:1]

        # Drop any trailing zeros
        while mant_data[-1:] == '0b0':
            del mant_data[-1:]
            exp = exp + 1 # Decreases mantissa order by 1,
                          # compensate by increasing the exponent

        # Drop the leading one from the mantissa
        del mant_data[0:1]
        mant_bits = mant_data.len
        exp += mant_bits


        # Find a minimum width exponent to make this a normal FPValue
        exp_bits = 2
        bias = (2**(exp_bits-1))-1
        biased_exp = exp - bias
        while biased_exp <= 0 or biased_exp >= (2**exp_bits)-1:
            exp_bits += 1
            bias = (2**(exp_bits-1))-1
            biased_exp = exp - bias

        exp_data = bitstring.Bits(bin=bin(biased_exp))
        assert(exp_data.len == exp_bits)

        return FPValue(sign, exp_data, mant_data)

# Actual representation of an IEEE-754 floating point value
# with a fixed exponent and mantissa bitwidth
class FPValue:
    def __init__(self, sign: bool, exp, mant):
        if isinstance(exp, bitstring.BitArray):
            exp = exp.copy()
        if isinstance(mant, bitstring.BitArray):
            mant = mant.copy()
        self._sign = bool(sign)
        self._exp = exp
        self._mant = mant
        assert isinstance(self._sign, bool)
        assert isinstance(self._exp, bitstring.Bits)
        assert isinstance(self._mant, bitstring.Bits)

    @classmethod
    def zero(cls, exp_width: int, mant_width: int):
        return cls(False, bitstring.Bits(exp_width), bitstring.Bits(mant_width))

    @classmethod
    def pos_inf(cls, exp_width: int, mant_width: int):
        exp = bitstring.BitArray(exp_width)
        exp.set(1)
        return cls(False, exp, bitstring.Bits(mant_width))

    @classmethod
    def neg_inf(cls, exp_width: int, mant_width: int):
        exp = bitstring.BitArray(exp_width)
        exp.set(1)
        return cls(True, exp, bitstring.Bits(mant_width))

    def is_negative(self):
        return self._sign
    def is_positive(self):
        return not self.is_negative()

    def is_nan(self):
        if self._exp.count(1) != self._exp.len:
            return False
        if self._mant.count(1) == 0:
            return False
        return True

    def is_inf(self):
        if self._exp.count(1) != self._exp.len:
            return False
        if self._mant.count(1) != 0:
            return False
        return True

    def is_normal(self):
        exp_popcount = self._exp.count(1)
        if exp_popcount == 0 or exp_popcount == self._exp.len:
            return False
        return True

    def is_subnormal(self):
        if self._exp.count(1) != 0:
            return False
        return True

    def mantissa_width(self) -> int:
        return self._mant.len
    def exponent_width(self) -> int:
        return self._exp.len

    def sign(self) -> bool:
        return self._sign
    def mantissa(self) -> bitstring.Bits:
        return self._mant
    def exponent(self) -> bitstring.Bits:
        return self._exp

    def inverted(self):
        return FPValue(not self._sign, self._exp, self._mant)

    def __repr__(self):
        if self.is_normal() or self.is_subnormal():
            return str(self.to_precise().approx_value())

        base = ""
        if self.is_nan():
            base = "NaN"
        elif self.is_inf():
            base = "Inf"
        else:
            raise RuntimeError("FPValue.__repr__ value is not normal,subnormal,NaN, or infinite!")

        if self.is_negative():
            base = "-" + base

        return base

    def succ(self):
        if self.is_nan():
            raise RuntimeError("Cannot take the successor of a NaN floating point value!")
        elif self.is_inf(): 
            if self.is_negative():
                exp = bitstring.BitArray(self.exponent_width())
                exp.set(1, range(0, exp.len - 1))
                mant = bitstring.BitArray(self.mantissa_width())
                mant.set(1)
                return FPValue(True, exp.copy(), mant.copy())
            else:
                return self
        elif self.is_subnormal():
            if self.is_positive():
                if self.mantissa().count(1) == self.mantissa_width():
                    # The next value is the smallest positive normal number
                    mant = bitstring.BitArray(self.mantissa_width())
                    exp = bitstring.BitArray(self.exponent_width())
                    exp.set(1, -1)
                    return FPValue(False, exp.copy(), mant.copy())
                else:
                    # The next value is still a positive subnormal
                    imant = self.mantissa().uint
                    imant += 1
                    mant = bitstring.BitArray(bin=bin(imant))
                    dropped_bits = self.mantissa_width() - mant.len
                    assert dropped_bits >= 0
                    mant = bitstring.BitArray(dropped_bits) + mant
                    return FPValue(False, self.exponent(), mant.copy())
            else:
                if self.mantissa().count(1) == 0:
                    # The next value is the smallest positive subnormal
                    # (We are negative zero)
                    mant = bitstring.BitArray(self.mantissa_width())
                    mant.set(1, -1)
                    exp = bitstring.BitArray(self.exponent_width())
                    return FPValue(False, exp.copy(), mant.copy())
                else:
                    # The next value is another negative subnormal
                    imant = self.mantissa().uint
                    imant -= 1
                    if imant == 0:
                        return FPValue.zero(self.exponent_width(), self.mantissa_width())
                    mant = bitstring.BitArray(bin=bin(imant))
                    dropped_bits = self.mantissa_width() - mant.len
                    assert dropped_bits >= 0
                    mant = bitstring.BitArray(dropped_bits) + mant
                    return FPValue(True, self.exponent(), mant.copy())
        else:
            # This is a normal number
            exp_mant = self.exponent() + self.mantissa()
            i_exp_mant = exp_mant.uint
            if self.is_positive():
                i_exp_mant += 1
            else:
                i_exp_mant -= 1
            exp_mant = bitstring.BitArray(bin=bin(i_exp_mant))
            dropped_bits = (self.exponent_width() + self.mantissa_width()) - exp_mant.len
            assert dropped_bits >= 0
            exp_mant = bitstring.BitArray(dropped_bits) + exp_mant
            exp = exp_mant[0:self.exponent_width()]
            mant = exp_mant[self.exponent_width():]
            assert(exp.len == self.exponent_width())
            assert(mant.len == self.mantissa_width())
            return FPValue(self.sign(), exp.copy(), mant.copy())

    def pred(self):
        if self.is_nan():
            raise RuntimeError("Cannot take the predecessor of a NaN floating point value!")
        return self.inverted().succ().inverted()

    def to_precise(self) -> PreciseFPValue:
        if self.is_inf():
            raise RuntimeError("Cannot convert infinite FPValue to a PreciseFPValue")
        if self.is_nan():
            raise RuntimeError("Cannot convert NaN FPValue to a PreciseFPValue")
        return PreciseFPValue.from_ieee754_bits(self._sign, self._exp, self._mant)

    def iter(self):
        def generator():
            value = self
            while True:
                yield value
                if value.is_inf() and value.is_positive():
                    return
                value = value.succ()
        return generator()

