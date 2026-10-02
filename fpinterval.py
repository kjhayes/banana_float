#! /usr/bin/python3

from banana import *

def main():

    one = PreciseFPValue.from_integer(1)

    rm = RoundToNearest()
    reals_around_one = rm.to_precise_interval(FPValue.from_f64(1.0))

    acc = reals_around_one
    step = reals_around_one

    COUNT = 1000
    for i in range(1,COUNT):
        fp_low = FPValue.from_precise(acc.low())
        fp_high = FPValue.from_precise(acc.high())
        print(i, fp_low.mantissa_width(), fp_high.mantissa_width())
        acc = acc + step

    return 0

if __name__ == "__main__":
    res = main()
    if res is None:
        res = 0
    exit(res)
