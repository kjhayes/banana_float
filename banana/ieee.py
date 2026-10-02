
import bitstring
import random
from .precise import *

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
    def neg_zero(cls, exp_width: int, mant_width: int):
        return cls(True, bitstring.Bits(exp_width), bitstring.Bits(mant_width))

    @classmethod
    def inf(cls, sign: bool, exp_width: int, mant_width: int):
        exp = bitstring.BitArray(exp_width)
        exp.set(1)
        return cls(sign, exp, bitstring.Bits(mant_width))

    @classmethod
    def pos_inf(cls, exp_width: int, mant_width: int):
        return cls.inf(False, exp_width, mant_width)

    @classmethod
    def neg_inf(cls, exp_width: int, mant_width: int):
        return cls.inf(True, exp_width, mant_width)

    @classmethod
    def random_normal(cls, exp_width: int, mant_width: int):
        sign = random.randint(0,1) == 1
        biased_exp = random.randint(1, (2**exp_width)-2)
        exp = integer_to_bits(biased_exp, exp_width)
        i_mant = random.randint(0, (2**mant_width)-1)
        mant = integer_to_bits(i_mant, mant_width)
        fp = FPValue(sign, exp, mant)
        assert fp.is_normal()
        return fp

    @classmethod
    def random_subnormal(cls, exp_width: int, mant_width: int):
        sign = random.randint(0,1) == 1
        exp = integer_to_bits(0, exp_width)
        i_mant = random.randint(0, (2**mant_width)-1)
        mant = integer_to_bits(i_mant, mant_width)
        fp = FPValue(sign, exp, mant)
        assert fp.is_subnormal()
        return fp

    @classmethod
    def from_f64(cls, value):
        bits = bitstring.BitArray(f"float64={value}")
        sign = bits[0:1] == '0b1'
        exp_data = bits[1:12] 
        mant_data = bits[12:64]
        return cls(sign, exp_data, mant_data)

    @classmethod
    def from_f32(cls, value):
        bits = bitstring.BitArray(f"float32={value}")
        sign = bits[0:1] == '0b1'
        exp_data = bits[1:9] 
        mant_data = bits[9:32]
        return cls(sign, exp_data, mant_data)

    def is_zero(self):
        return (self._exp + self._mant).count(1) == 0

    def is_negative(self):
        return self._sign

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

    @classmethod
    def exponent_bias(cls, exp_width: int):
        return (2**(exp_width-1))-1

    def bias(self) -> int:
        return FPValue.exponent_bias(self.exponent_width())

    def biased_exponent(self) -> int:
        return self._exp.uint
    def unbiased_exponent(self) -> int:
        return self.biased_exponent() - self.bias()

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
            return self

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
            if self.is_negative():
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
                    mant = integer_to_bits(imant, self.mantissa_width())
                    return FPValue(True, self.exponent(), mant.copy())
            else:
                # Positive or Zero
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
                    mant = integer_to_bits(imant, self.mantissa_width())
                    return FPValue(False, self.exponent(), mant.copy())
        else:
            # This is a normal number
            exp_mant = self.exponent() + self.mantissa()
            i_exp_mant = exp_mant.uint
            if self.is_negative():
                i_exp_mant -= 1
            else:
                i_exp_mant += 1
            exp_mant = integer_to_bits(i_exp_mant, self.exponent_width() + self.mantissa_width())
            exp = exp_mant[0:self.exponent_width()]
            mant = exp_mant[self.exponent_width():]
            assert(exp.len == self.exponent_width())
            assert(mant.len == self.mantissa_width())
            return FPValue(self.sign(), exp.copy(), mant.copy())

    def pred(self):
        if self.is_nan():
            return self
        return self.inverted().succ().inverted()

    def cast_below(self, exp_width: int, mant_width: int):
        return self.to_precise().imprecise_below(exp_width, mant_width)

    def to_precise(self) -> PreciseFPValue:
        if self.is_inf():
            return PreciseFPValue(-1 if self.sign() else 1, 0, is_inf=True)
        if self.is_nan():
            raise RuntimeError("Cannot convert NaN FPValue to a PreciseFPValue")
        return PreciseFPValue.from_ieee754_bits(self._sign, self._exp, self._mant)

    def __eq__(self, other):
        assert isinstance(other, FPValue)
        if self.is_nan() or other.is_nan():
            return False
        # Not NaN

        if self.is_inf():
            if other.is_inf():
                return self.sign() == other.sign()
            else:
                return False
        if other.is_inf():
            return False
        # Not Inf

        return self.to_precise() == other.to_precise()

    @classmethod
    def from_precise(cls, precise):
        sign = precise.base < 0
        base = abs(precise.base)
        if base == 0:
            return FPValue(False, bitstring.Bits('0b0'), bitstring.Bits('0b0'))
        exp = precise.exp

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

        # Find a minimum width exponent to make this a normal
        exp_bits = 2
        bias = (2**(exp_bits-1))-1
        biased_exp = exp - bias
        while biased_exp <= 0 or biased_exp >= (2**exp_bits)-1:
            exp_bits += 1
            bias = (2**(exp_bits-1))-1
            biased_exp = exp + bias

        exp_data = integer_to_bits(biased_exp, exp_bits)

        return FPValue(sign, exp_data, mant_data)

    # Comparison Operations
    def __lt__(self, other):
        assert isinstance(other, FPValue)
        if self.is_nan() or other.is_nan():
            return False
        # Not NaN

        if self.is_inf():
            if not self.is_negative():
                return False
            if other.is_inf() and other.is_negative():
                return False
            return True
        if other.is_inf():
            if other.is_negative():
                return False
            else:
                return True
        # Not Inf

        return self.to_precise() < other.to_precise()

    def __le__(self, other):
        assert isinstance(other, FPValue)
        if self.is_nan() or other.is_nan():
            return False
        return self < other or self == other

    def __gt__(self, other):
        assert isinstance(other, FPValue)
        if self.is_nan() or other.is_nan():
            return False
        return not (self <= other)

    def __ge__(self, other):
        assert isinstance(other, FPValue)
        if self.is_nan() or other.is_nan():
            return False
        return not (self < other)

    # Forward/Backward Iterators
    def iter(self):
        def generator():
            value = self
            while True:
                yield value
                if value.is_inf() and not value.is_negative():
                    return
                value = value.succ()
        return generator()

    def reverse_iter(self):
        def generator():
            value = self
            while True:
                yield value
                if value.is_inf() and value.is_negative():
                    return
                value = value.pred()
        return generator()


