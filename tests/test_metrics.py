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


def test_regional_platforms():
    num = ioos_metrics.regional_platforms()
    assert isinstance(num, int)
    assert num >= 0


def test_atn_deployments():
    num = ioos_metrics.atn_deployments()
    assert isinstance(num, int)
    assert num >= 0


def test_ott_projects():
    num = ioos_metrics.ott_projects()
    assert isinstance(num, int)
    assert num >= 0


def test_qartod_manuals():
    num = ioos_metrics.qartod_manuals()
    assert isinstance(num, int)
    assert num >= 0


def test_ioos_core_variables():
    num = ioos_metrics.ioos_core_variables()
    assert isinstance(num, int)
    assert num >= 0
