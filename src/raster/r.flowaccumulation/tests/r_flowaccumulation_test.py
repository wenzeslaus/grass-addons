"""Tests of r.flowaccumulation.

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
    pytest.param("degree", "degree", marks=MIRRORED_DEGREE),
    pytest.param("auto", "degree", marks=MIRRORED_DEGREE),
]
N = np.nan


def read_with_nulls(session, name):
    """Read a raster as an array with NaN for nulls"""
    return garray.array(name, null="nan", dtype=np.float64, env=session.env)


@pytest.mark.parametrize(
    ("direction_format", "suffix", "flags", "accumulation_type"),
    [
        ("45degree", "45degree", "", "CELL"),
        pytest.param("degree", "degree", "", "CELL", marks=MIRRORED_DEGREE),
        pytest.param("auto", "degree", "", "CELL", marks=MIRRORED_DEGREE),
        ("power2", "power2", "", "CELL"),
        ("auto", "45degree", "", "CELL"),
        ("auto", "power2", "", "CELL"),
        ("45degree", "45degree", "m", "CELL"),
        ("45degree", "45degree", "", "FCELL"),
        ("45degree", "45degree", "", "DCELL"),
    ],
)
def test_converging(session, direction_format, suffix, flags, accumulation_type):
    """Accumulation of all eight directions is the same in each format and mode"""
    tools = Tools(session=session)
    accumulation = tools.r_flowaccumulation(
        direction=f"converging_{suffix}",
        format=direction_format,
        flags=flags,
        type=accumulation_type,
        output=np.array,
    )
    expected = [
        [1, 1, 1, 1, 1, 1, 1],
        [3, 2, 1, 2, 1, 2, 3],
        [15, 4, 1, 5, 6, 9, 20],
        [3, 2, 1, 2, 1, 2, 3],
        [1, 1, 1, 1, 1, 1, 1],
    ]
    np.testing.assert_array_equal(accumulation, expected)


@pytest.mark.parametrize(("direction_format", "suffix"), FORMATS)
def test_east(session, direction_format, suffix):
    """Accumulation increases eastward when all cells point East"""
    tools = Tools(session=session)
    accumulation = tools.r_flowaccumulation(
        direction=f"east_{suffix}", format=direction_format, output=np.array
    )
    np.testing.assert_array_equal(accumulation, [[1, 2, 3, 4, 5, 6, 7]] * 5)


def test_null(session):
    """Null directions are null and break the flow path"""
    tools = Tools(session=session, overwrite=True)
    tools.r_flowaccumulation(
        direction="east_null", format="45degree", output="accumulation"
    )
    accumulation = read_with_nulls(session, "accumulation")
    np.testing.assert_array_equal(accumulation, [[1, 2, 3, N, 1, 2, 3]] * 5)


@pytest.mark.parametrize(
    ("weight", "flags", "expected_row"),
    [
        ("col_weight", "", [1, 3, 6, 10, 15, 21, 28]),
        ("col_weight", "m", [1, 3, 6, 10, 15, 21, 28]),
        # Null weights break the flow path like null directions (current
        # implementation, not documented).
        ("null_weight", "", [1, 3, 6, N, 5, 11, 18]),
        ("null_weight", "n", [1, 3, 6, 6, 11, 17, 24]),
    ],
)
def test_weight(session, weight, flags, expected_row):
    """Weighted accumulation sums the weights of the cells along the path"""
    tools = Tools(session=session, overwrite=True)
    tools.r_flowaccumulation(
        direction="east_45degree",
        format="45degree",
        weight=weight,
        flags=flags,
        output="accumulation",
    )
    accumulation = read_with_nulls(session, "accumulation")
    np.testing.assert_array_equal(accumulation, [expected_row] * 5)
