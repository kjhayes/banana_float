
import math
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

    def __init__(self, base: int, exp: int, is_inf=False):

        self.is_inf = is_inf
        if self.is_inf:
            self.base = -1 if base < 0 else 1
            self.exp = 0
            return

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
                base = -1 if sign else 1
                return cls(base, 0, True)
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

    def imprecise_below(self, exp_width: int, mant_width: int):
        from .ieee import FPValue

        if self.is_inf:
            if self.is_negative():
                return FPValue.neg_inf(exp_width, mant_width)
            else:
                return FPValue.pos_inf(exp_width, mant_width).pred()

        if self.base == 0:
            return FPValue.zero(exp_width, mant_width)

        mant = bitstring.BitArray(integer_to_bits(abs(self.base), None))

        # Drop any leading zero(s)
        while mant[0:1] == '0b0':
            del mant[0:1]

        # Drop the leading one
        del mant[0:1]

        bias = (2**(exp_width-1))-1
        unbiased_exp = self.exp + mant.len
        biased_exp = unbiased_exp + bias

        if mant.len < mant_width:
            mant = mant + bitstring.Bits(mant_width - mant.len)

        if biased_exp <= 0:
            # Subnormal Range
            # print(f"Subnormal(unbiased={unbiased_exp},biased={biased_exp}): ", end='')

            # Add back in the leading 1
            mant = '0b1' + mant
            del mant[-1]
            unbiased_exp += 1
            biased_exp += 1

            subnormal_exp = 1-bias
            exp_diff = subnormal_exp - unbiased_exp
            assert exp_diff >= 0


            # Shift by the exponent difference
            mant = mant >> exp_diff

            exp = integer_to_bits(0, exp_width)
            mant = mant[0:mant_width]
            assert mant.len == mant_width

            fp = FPValue(self.sign(), exp, mant)
            if self.is_negative():
                while fp.to_precise() > self:
                    fp = fp.pred()

            return fp

        elif biased_exp >= (2**exp_width)-1:
            # Overflow Range
            # print(f"Overflow(unbiased={unbiased_exp},biased={biased_exp}): ", end='')
            if self.is_negative():
                return FPValue.neg_inf(exp_width, mant_width)
            else:
                return FPValue.pos_inf(exp_width, mant_width).pred()
        else:
            # Normal Range
            # print(f"Normal(unbiased={unbiased_exp},biased={biased_exp}): ", end='')
            exp = integer_to_bits(biased_exp, exp_width)
            mant = mant[0:mant_width]
            assert mant.len == mant_width
            fp = FPValue(self.sign(), exp, mant)
            if self.is_negative():
                while fp.to_precise() > self:
                    fp = fp.pred()
            return fp


    def approx_value(self):
        if self.is_inf:
            if self.sign():
                return -math.inf
            else:
                return math.inf
        return self.base * 2**self.exp

    def __repr__(self):
        if self.is_inf:
            if self.sign():
                return "-Inf"
            else:
                return "Inf"

        return f"{self.base}*2**{self.exp}"

    @classmethod
    def scale_pair(cls, left, right):
        assert(isinstance(left, PreciseFPValue))
        assert(isinstance(right, PreciseFPValue))
        assert not left.is_inf
        assert not right.is_inf
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

    def sign(self):
        return self.base < 0

    def is_negative(self):
        return self.base < 0

    def __add__(self, other):
        other = PreciseFPValue.coerce(other)
        if self.is_inf:
            if other.is_inf:
                if self.base == other.base:
                    return self
                else:
                    raise RuntimeError("PreciseFPValue: cannot add +Inf and -Inf")
            else:
                return self
        if other.is_inf:
            return other

        s_base, o_base, exp = PreciseFPValue.scale_pair(self,other)
        return PreciseFPValue(s_base + o_base, exp)

    def __neg__(self):
        return PreciseFPValue(-self.base, self.exp, is_inf=self.is_inf)

    def __sub__(self, other):
        other = PreciseFPValue.coerce(other)
        return self + (-other)

    def __mul__(self, other):
        other = PreciseFPValue.coerce(other)
        if self.is_inf:
            if other.is_inf:
                if self.base == other.base:
                    return self
                else:
                    raise RuntimeError("PreciseFPValue: cannot multiply +Inf and -Inf")
            else:
                return self
        if other.is_inf:
            return other
        base = self.base * other.base
        exp = self.exp + other.exp
        return PreciseFPValue(base, exp)

    def __eq__(self, other):
        other = PreciseFPValue.coerce(other)
        return self.base == other.base and self.exp == other.exp and self.is_inf == other.is_inf

    def __lt__(self, other):
        other = PreciseFPValue.coerce(other)
        if self.is_inf:
            if self.sign():
                return True
            else:
                return False
        if other.is_inf:
            if other.sign():
                return False
            else:
                return True

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
        if self.is_inf:
            if other.is_inf:
                raise RuntimeError("PreciseFPValue: Cannot divide infinite values!")
            else:
                return self
        if other.is_inf:
            return PreciseFPValue.from_integer(0)

        if self.base % other.base == 0:
            return PreciseFPValue(self.base // other.base, self.exp - other.exp)
        raise RuntimeError(f"Cannot divide PreciseFPValue {self} by {other} without rounding!")

