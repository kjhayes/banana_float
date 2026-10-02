
from abc import ABC,abstractmethod
from .precise import *
from .ieee import *
from .interval import *

class RoundingMode(ABC):
    @abstractmethod
    def to_precise_interval(self, x: FPValue) -> PreciseFPInterval:
        assert False

class RoundToNearest(RoundingMode):
    def to_precise_interval(self, x: FPValue) -> PreciseFPInterval:
        pred = x.pred()
        succ = x.succ()
        if pred.is_inf():
            low = None
        else:
            low = (pred.to_precise() + x.to_precise()) / 2
        if succ.is_inf():
            high = None
        else:
            high = (succ.to_precise() + x.to_precise()) / 2
        return PreciseFPInterval(low, high)

