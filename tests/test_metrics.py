import sys

import pandas as pd

sys.path.append("..")

from ioos_metrics import ioos_metrics


def test_previous_metrics():
    df = ioos_metrics.previous_metrics()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty


def test_federal_partners():
    num = ioos_metrics.federal_partners()
    assert isinstance(num, int)


def test_ngdac_gliders():
    num = ioos_metrics.ngdac_gliders()
    assert isinstance(num, int)
