
import bitstring
from .util import integer_to_bits

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
        if self.base == 0:
            self.exp = 0
        else:
            self.exp = exp

    @classmethod
    def from_ieee754_bits(cls, sign: bool, exp_data, mant_data):

        exp_data = bitstring.BitArray(exp_data.copy())
        mant_data = bitstring.BitArray(mant_data.copy())

        exp_bits = exp_data.len
        bias = (2**(exp_bits-1))-1

        popcount = exp_data.count(1)
        if popcount == exp_bits:
            # NaN or Inf
            if mant_data.count(1) == 0:
                raise RuntimeError("Cannot encode (+-)Inf as PreciseFPValue!")
            else:
                raise RuntimeError("Cannot encode NaN as PreciseFPValue!")

        subnormal = popcount == 0

        biased_exp = exp_data.uint
        unbiased_exp = biased_exp - bias

        unbiased_exp += 1
        if not subnormal:
            mant_data = '0b1' + mant_data

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
        return f"{self.base}*2**{self.exp}"

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

    def __le__(self, other):
        return self < other or self == other

    def __gt__(self, other):
        return not (self <= other)

    def __ge__(self, other):
        return not (self < other)

    def __truediv__(self, other):
        other = PreciseFPValue.coerce(other)
        if self.base % other.base == 0:
            return PreciseFPValue(self.base // other.base, self.exp - other.exp)
        raise RuntimeError(f"Cannot divide PreciseFPValue {self} by {other} without rounding!")

class PreciseFPInterval:
    def __init__(self, low: PreciseFPValue, high: PreciseFPValue):
        self._low = low
        self._high = high

    def low(self):
        return self._low
    def high(self):
        return self._high

    @classmethod
    def coerce(cls, value):
        if isinstance(value, PreciseFPInterval):
            return value
        # Try to coerce to a PreciseFPValue
        value = PreciseFPValue.coerce(value)
        return PreciseFPInterval(value, value)

    def __add__(self, other):
        other = PreciseFPInterval.coerce(other)
        return PreciseFPInterval(self.low() + other.low(), self.high() + other.high())

