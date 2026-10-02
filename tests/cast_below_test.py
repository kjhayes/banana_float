
from banana import *

RANDOM_TEST_REPEATS = 1000

def cast_below_run_test(x, exp_step, mant_step, num_steps):
    exp_width = x.exponent_width()
    mant_width = x.mantissa_width()
    for i in range(num_steps):
        exp_width += exp_step
        mant_width += mant_step
        y = x.cast_below(exp_width, mant_width)
        assert y.exponent_width() == exp_width
        assert y.mantissa_width() == mant_width
        assert y <= x
        assert y.succ() >= x
        x = y

def test_random_normal_grow_exponent_cast_below():
    exp_width = 4
    mant_width = 4
    for i in range(RANDOM_TEST_REPEATS):
        x = FPValue.random_normal(exp_width,mant_width)
        cast_below_run_test(x, 1, 0, 10)

def test_random_normal_grow_mantissa_cast_below():
    exp_width = 4
    mant_width = 4
    for i in range(RANDOM_TEST_REPEATS):
        x = FPValue.random_normal(exp_width,mant_width)
        cast_below_run_test(x, 0, 1, 10)

def test_random_normal_grow_both_cast_below():
    exp_width = 4
    mant_width = 4
    for i in range(RANDOM_TEST_REPEATS):
        x = FPValue.random_normal(exp_width,mant_width)
        cast_below_run_test(x, 1, 1, 10)

def test_random_subnormal_grow_exponent_cast_below():
    exp_width = 4
    mant_width = 4
    for i in range(RANDOM_TEST_REPEATS):
        x = FPValue.random_subnormal(exp_width,mant_width)
        cast_below_run_test(x, 1, 0, 10)

def test_random_subnormal_grow_mantissa_cast_below():
    exp_width = 4
    mant_width = 4
    for i in range(RANDOM_TEST_REPEATS):
        x = FPValue.random_subnormal(exp_width,mant_width)
        cast_below_run_test(x, 0, 1, 10)

def test_random_subnormal_grow_both_cast_below():
    exp_width = 4
    mant_width = 4
    for i in range(RANDOM_TEST_REPEATS):
        x = FPValue.random_subnormal(exp_width,mant_width)
        cast_below_run_test(x, 1, 1, 10)

def test_random_normal_shrink_exponent_cast_below():
    exp_width = 8
    mant_width = 23
    for i in range(RANDOM_TEST_REPEATS):
        x = FPValue.random_normal(exp_width,mant_width)
        cast_below_run_test(x, -1, 0, 5)

def test_random_normal_shrink_mantissa_cast_below():
    exp_width = 8
    mant_width = 23
    for i in range(RANDOM_TEST_REPEATS):
        x = FPValue.random_normal(exp_width,mant_width)
        cast_below_run_test(x, 0, -1, 5)

def test_random_normal_shrink_both_cast_below():
    exp_width = 8
    mant_width = 23
    for i in range(RANDOM_TEST_REPEATS):
        x = FPValue.random_normal(exp_width,mant_width)
        cast_below_run_test(x, -1, -1, 5)

def test_random_subnormal_shrink_exponent_cast_below():
    exp_width = 8
    mant_width = 23
    for i in range(RANDOM_TEST_REPEATS):
        x = FPValue.random_subnormal(exp_width,mant_width)
        cast_below_run_test(x, -1, 0, 5)

def test_random_subnormal_shrink_mantissa_cast_below():
    exp_width = 8
    mant_width = 23
    for i in range(RANDOM_TEST_REPEATS):
        x = FPValue.random_subnormal(exp_width,mant_width)
        cast_below_run_test(x, 0, -1, 5)

def test_random_subnormal_shrink_both_cast_below():
    exp_width = 8
    mant_width = 23
    for i in range(RANDOM_TEST_REPEATS):
        x = FPValue.random_subnormal(exp_width,mant_width)
        cast_below_run_test(x, -1, -1, 5)

def test_all_fp16_to_fp8():
    x_exp_width = 5
    x_mant_width = 10
    y_exp_width = 4
    y_mant_width = 3
    for i,x in enumerate(FPValue.neg_inf(x_exp_width, x_mant_width).iter()):
        y = x.cast_below(y_exp_width, y_mant_width)
        # print(i,x,y)
        assert y.exponent_width() == y_exp_width
        assert y.mantissa_width() == y_mant_width
        assert y.to_precise() <= x.to_precise()
        assert y.succ() >= x

