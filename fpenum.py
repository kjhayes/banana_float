#! /usr/bin/python3

from banana import *
import argparse as argp

def main():
    parser = argp.ArgumentParser()
    parser.add_argument("exp_width")
    parser.add_argument("mant_width")

    args = parser.parse_args()

    exp_width = int(args.exp_width)
    mant_width = int(args.mant_width)

    for x in FPValue.neg_inf(exp_width,mant_width).iter():
        if x.is_subnormal():
            print("*",end='')
        print(x)

if __name__ == "__main__":
    main()
    exit(0)

