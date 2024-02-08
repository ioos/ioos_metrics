import sys

sys.path.append("..")

from ioos_metrics import ioos_metrics


def test_federal_partners():
    num = ioos_metrics.federal_partners()
    assert isinstance(num, int) 