
import bitstring
from abc import ABC,abstractmethod
import random

def integer_to_bits(i: int, width: int):
    bits = bitstring.Bits(bin=bin(i))
    dropped_bits = width - bits.len
    if dropped_bits < 0:
        raise RuntimeError(f"Cannot convert integer {i} to bit representation of width {width}!")
    return bitstring.Bits(dropped_bits) + bits

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
            raise RuntimeError("Cannot take the predecessor of a NaN floating point value!")
        return self.inverted().succ().inverted()

    def cast_below_mantissa(self, mant_width: int):
        if mant_width < self.mantissa_width():
            return self.cast_below_shrink_mantissa(self.mantissa_width() - mant_width)
        if mant_width > self.mantissa_width():
            return self.cast_below_grow_mantissa(mant_width - self.mantissa_width())
        else:
            return self

    def cast_below_shrink_mantissa(self, mant_sub: int):
        if self.is_inf():
            return FPValue.inf(self.sign(), self.exponent_width(), self.mantissa_width() - mant_sub)
        elif self.is_nan():
            mant = bitstring.BitArray(self.mantissa())
            del mant[-mant_sub:]
            if mant.count(1) == 0:
                mant.set(1, -1)
            return FPValue(self.sign(), self.exponent(), mant)

        # Normal or Subnormal

        mant = bitstring.BitArray(self.mantissa())
        dropping = mant[-mant_sub:]
        if not self.is_negative() or dropping.count(1) == 0:
            del mant[-mant_sub:]
            return FPValue(self.sign(), self.exponent(), mant)
        else:
            # We are negative and so dropping non-zero
            # mantissa bits will actually *increase* our
            # relative value
            #
            # Do it anyways and then backtrack until we are
            # small enough
            # (SLOW) TODO: Do something cleverer to be fast
            del mant[-mant_sub:]
            fp = FPValue(self.sign(), self.exponent(), mant)
            while fp > self:
                fp = fp.pred()
            return fp

    def cast_below_grow_mantissa(self, mant_add: int):
        # Just append some zeros onto the end
        zeros = bitstring.Bits(mant_add)
        return FPValue(self.sign(), self.exponent(), self.mantissa() + zeros)

    def cast_below_exponent(self, exp_width: int):
        if exp_width < self.exponent_width():
            return self.cast_below_shrink_exponent(self.exponent_width() - exp_width)
        if exp_width > self.exponent_width():
            return self.cast_below_grow_exponent(exp_width - self.exponent_width())
        else:
            return self

    def cast_below_shrink_exponent(self, exp_sub: int):
        assert exp_sub < self.exponent_width()
        if self.is_inf() or self.is_nan():
            return FPValue(self.sign(), self.exponent()[0:-exp_sub], self.mantissa())

        exp_width = self.exponent_width() - exp_sub
        assert exp_width > 0

        if self.is_subnormal():
            old_subnormal_unbiased = 1-self.bias()
            new_subnormal_unbiased = 1-FPValue.exponent_bias(exp_width)
            order_diff = new_subnormal_unbiased - old_subnormal_unbiased
            mant = self.mantissa() >> order_diff
            fp = FPValue(self.sign(), integer_to_bits(0,exp_width), mant)
            if self.sign():
                while fp > self:
                    fp = fp.pred()
            return fp

        # We are normal
        unbiased = self.unbiased_exponent()
        bias = FPValue.exponent_bias(self.exponent_width() - exp_sub)
        new_biased = unbiased + bias
        if 0 < new_biased and new_biased < (2**exp_width)-1:
            # The result can be normal
            exp = integer_to_bits(new_biased, exp_width)
            return FPValue(self.sign(), exp, self.mantissa())

        if new_biased >= (2**exp_width)-1:
            # We overflow
            if self.is_negative():
                return FPValue.neg_inf(exp_width, self.mantissa_width())
            else:
                return FPValue.pos_inf(exp_width, self.mantissa_width()).pred()

        # We underflow to subnormal
        mant = bitstring.BitArray(self.mantissa())

        # Materialize the implicit leading 1
        mant = mant >> 1 # This drops a bit
        mant.set(1,0)

        old_normal_unbiased = self.unbiased_exponent()+1
        new_subnormal_unbiased = 1-FPValue.exponent_bias(exp_width)
        order_diff = new_subnormal_unbiased - old_normal_unbiased
        assert order_diff >= 0
        mant = mant >> order_diff
        fp = FPValue(self.sign(), integer_to_bits(0, exp_width), mant)
        if self.sign():
            while fp > self:
                fp = fp.pred()
        return fp

    def cast_below_grow_exponent(self, exp_add: int):
        assert exp_add > 0

        exp_width = self.exponent_width() + exp_add

        if self.is_nan() or self.is_inf():
            fill = bitstring.Bits(exp_add)
            fill.set(1)
            return FPValue(self.sign(), self.exponent() + fill, self.mantissa())

        # Growing the exponent
        unbiased = self.unbiased_exponent()
        new_bias = FPValue.exponent_bias(exp_width)
        new_biased = unbiased + new_bias
        assert new_biased >= 0

        if self.is_normal():
            # Normal -> Normal, we can just use the same mantissa

            # assert that the new exponent will still result in a normal value,
            # should always be the case if we grow the exponent width
            assert new_biased > 0 and new_biased < (2**new_bias)-1

            exp = integer_to_bits(new_biased, exp_width)
            return FPValue(self.sign(), exp, self.mantissa())

        else:
            # We need to shift the mantissa trying to drop
            # the most significant one's bit. Every time we do,
            # the exponent needs to decrease by one to compensate.
            mant = bitstring.BitArray(self.mantissa())
            while mant[0:1] == '0b0' and new_biased > 1:
                del mant[0:1]
                mant = mant + '0b0'
                unbiased -= 1
                new_biased -= 1

            if new_biased <= 1:
                # Subnormal -> Subnormal
                exp = integer_to_bits(0, exp_width)
                fp = FPValue(self.sign(), exp, mant)
                return fp
            else:
                # Subnormal -> Normal
                assert mant[0:1] == '0b1'
                del mant[0:1]
                mant = mant + '0b0'
                exp = integer_to_bits(new_biased, exp_width)
                fp = FPValue(self.sign(), exp, mant)
                return fp

    # Cast to the corresponding width and if rounding is required,
    # always round "down" so that x.cast_below() <= x always.
    def cast_below(self, exp_width: int, mant_width: int):
        # First cast mantissa, then exponent: TODO Check that this is fine... -KJH
        return self.cast_below_mantissa(mant_width).cast_below_exponent(exp_width)

    def to_precise(self) -> PreciseFPValue:
        if self.is_inf():
            raise RuntimeError("Cannot convert infinite FPValue to a PreciseFPValue")
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


