import sys

import pandas as pd
import pytest

sys.path.append("..")

from ioos_metrics import ioos_metrics
from ioos_metrics.ioos_metrics import (
    atn_deployments,
    comt,
    federal_partners,
    hab_pilot_projects,
    ioos_core_variables,
    mbon_projects,
    metadata_records,
    ngdac_gliders,
    ott_projects,
    qartod_manuals,
    regional_associations,
    regional_platforms,
)


@pytest.fixture
def df_previous_metrics():
    return ioos_metrics.previous_metrics()


def test_previous_metrics(df_previous_metrics):
    assert isinstance(df_previous_metrics, pd.DataFrame)
    assert not df_previous_metrics.empty


def test_ngdac_gliders(df_previous_metrics):
    num = ioos_metrics.ngdac_gliders()
    # New count should always be >= than the previous one.
    assert num >= df_previous_metrics["NGDAC Glider Days"].iloc[-1]


def test_ioos():
    num = ioos_metrics.ioos()
    assert num == 1


def test_if_metric_is_a_natural_number():
    functions = [
        atn_deployments,
        comt,
        federal_partners,
        hab_pilot_projects,
        ioos_core_variables,
        mbon_projects,
        metadata_records,
        ngdac_gliders,
        ott_projects,
        qartod_manuals,
        regional_associations,
        regional_platforms,
    ]
    for function in functions:
        num = function()
        assert isinstance(num, int)
        assert num >= 0
