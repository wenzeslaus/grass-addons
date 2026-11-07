"""Tests of r.hydrobasin.

SPDX-FileCopyrightText: 2026 Vaclav Petras
SPDX-License-Identifier: GPL-2.0-or-later
"""

import numpy as np
import pytest

import grass.script.array as garray
from grass.tools import Tools

MIRRORED_DEGREE = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="degree format directions are converted incorrectly",
)
FORMATS = [
    ("45degree", "45degree"),
    ("auto", "45degree"),
    pytest.param("degree", "degree", marks=MIRRORED_DEGREE),
    pytest.param("auto", "degree", marks=MIRRORED_DEGREE),
]
N = np.nan


def read_with_nulls(session, name):
    """Read a raster as an array with NaN for nulls"""
    return garray.array(name, null="nan", dtype=np.float64, env=session.env)


@pytest.mark.parametrize("flags", ["", "m"])
@pytest.mark.parametrize(
    ("direction_format", "suffix"),
    [*FORMATS, ("power2", "power2"), ("auto", "power2")],
)
def test_converging(session, direction_format, suffix, flags):
    """Watersheds of all eight directions are the same in each format"""
    tools = Tools(session=session)
    watersheds = tools.r_hydrobasin(
        direction=f"converging_{suffix}",
        format=direction_format,
        outlets="converging_outlets",
        flags=flags,
        output=np.array,
    )
    np.testing.assert_array_equal(watersheds, [[1, 1, 1, 2, 2, 2, 2]] * 5)


@pytest.mark.parametrize(("direction_format", "suffix"), FORMATS)
def test_east(session, direction_format, suffix):
    """Each row is a watershed when all cells point East

    Negative edge values as produced by r.watershed are accepted.
    """
    tools = Tools(session=session)
    watersheds = tools.r_hydrobasin(
        direction=f"east_{suffix}",
        format=direction_format,
        outlets="east_outlets",
        output=np.array,
    )
    np.testing.assert_array_equal(watersheds, [[row] * 7 for row in range(1, 6)])


@pytest.mark.parametrize(
    ("column", "upstream_id", "downstream_id"), [("cat", 1, 2), ("id", 10, 20)]
)
def test_nested_outlets(session, column, upstream_id, downstream_id):
    """An outlet upstream of another outlet splits its watershed"""
    tools = Tools(session=session)
    output = f"watersheds_nested_{column}"
    tools.r_hydrobasin(
        direction="east_45degree",
        format="45degree",
        outlets="nested_outlets",
        column=column,
        output=output,
    )
    watersheds = read_with_nulls(session, output)
    expected = np.full((5, 7), N)
    expected[2] = [upstream_id] * 4 + [downstream_id] * 3
    np.testing.assert_array_equal(watersheds, expected)
