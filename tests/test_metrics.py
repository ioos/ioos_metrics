import sys

import pandas as pd
import pytest

sys.path.append("..")

from ioos_metrics import ioos_metrics


@pytest.fixture
def df_previous_metrics():
    return ioos_metrics.previous_metrics()


def test_previous_metrics(df_previous_metrics):
    assert isinstance(df_previous_metrics, pd.DataFrame)
    assert not df_previous_metrics.empty


def test_federal_partners():
    num = ioos_metrics.federal_partners()
    # must the an integer and cannot be less than 0
    assert isinstance(num, int)
    assert num >= 0


def test_ngdac_gliders(df_previous_metrics):
    num = ioos_metrics.ngdac_gliders()
    assert isinstance(num, int)
    # New count should always be >= than the previous one.
    assert num >= df_previous_metrics["NGDAC Glider Days"].iloc[-1]


def test_comt():
    num = ioos_metrics.comt()
    assert isinstance(num, int)
    assert num >= 0


def test_regional_associations():
    num = ioos_metrics.regional_associations()
    assert isinstance(num, int)
    assert num >= 0
