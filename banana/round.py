
from abc import ABC,abstractmethod
from .precise import *
from .ieee import *

class RoundingMode(ABC):

    @abstractmethod
    def to_interval(self, x: FPValue) -> PreciseFPInterval:
        assert False

    @abstractmethod
    def from_interval(self, i: PreciseFPInterval) -> FPValue:
        assert False

class RoundToNearest(RoundingMode):
    def to_interval(self, x: FPValue):
        assert False
    def from_interval(self, i: PreciseFPInterval):
        assert False

