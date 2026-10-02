
from .precise import *
from .ieee import *

# low = None -> low = -Inf
# high = None -> high = Inf
class PreciseFPInterval:
    def __init__(self, low: PreciseFPValue|None, high: PreciseFPValue|None):
        if low is not None and high is not None:
            assert low <= high
        self._low = low
        self._high = high

    def low(self):
        return self._low
    def high(self):
        return self._high

    def fp_low(self, exp_bits, mant_bits):
        if self.high() is None:
            return FPValue.pos_inf(exp_bits, mant_bits)
        fp = FPValue.from_precise(self.low())
        fp = fp.cast_below(exp_bits, mant_bits)
        return fp

    def fp_high(self, exp_bits, mant_bits):
        if self.high() is None:
            return FPValue.pos_inf(exp_bits, mant_bits)
        fp = FPValue.from_precise(self.high())
        fp = fp.cast_above(exp_bits, mant_bits)
        return fp

    def contains(self, other):
        assert isinstance(other, PreciseFPInterval)
        if self._low is not None:
            if other.low() is None:
                return False
            if self._low > other.low():
                return False
        if self._high is not None:
            if other.high() is None:
                return False
            if self._high < other.high():
                return False
        return True

    def width(self):
        if self.low() is None or self.high() is None:
            return None
        else:
            return self.high() - self.low()


    def to_fp_interval(self, exp_width, mant_width):
        return FPInterval(
                self.fp_low(exp_width, mant_width),
                self.fp_high(exp_width, mant_width))

    def __add__(self, other):
        if self.low() is None or other.low() is None:
            low = None
        else:
            low = self.low() + other.low()
        if self.high() is None or other.high() is None:
            high = None
        else:
            high = self.high() + other.high()
        return PreciseFPInterval(low, high)

    def __neg__(self):
        if self.low() is None:
            high = None
        else:
            high = -self.low()
        if self.high() is None:
            low = None
        else:
            low = -self.high()
        return PreciseFPInterval(low, high)

    def __sub__(self, other):
        return self + (-other)

    def __repr__(self):
        if self.low() is None:
            low = "(-Inf"
        else:
            low = "[" + repr(self.low())
        if self.high() is None:
            high = "Inf)"
        else:
            high = repr(self.high()) + "]"
        return low + "," + high

class FPInterval:
    def __init__(self, low: FPValue, high: FPValue):
        assert low.exponent_width() == high.exponent_width()
        assert low.mantissa_width() == high.mantissa_width()
        assert low <= high
        self._low = low
        self._high = high

    def low(self):
        return self._low
    def high(self):
        return self._high

    def to_precise_interval(self):
        return PreciseFPInterval(
                self.low().to_precise(),
                self.high().to_precise())

    def __repr__(self):
        return f"[{self.low()},{self.high()}]"

