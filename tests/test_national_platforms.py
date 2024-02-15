"""Test national platforms."""


import sys

sys.path.append("..")

from ioos_metrics.national_platforms import (
    get_coops,
    get_ndbc,
    get_nerrs,
)


def test_if_metric_is_a_natural_number():
    functions = [
        get_coops,
        get_ndbc,
        get_nerrs,
    ]
    for function in functions:
        num = function()
        assert isinstance(num, int)
        assert num >= 0
