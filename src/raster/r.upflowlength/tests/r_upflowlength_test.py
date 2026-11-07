"""Tests of r.upflowlength.

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


def read_with_nulls(session, name):
    """Read a raster as an array with NaN for nulls

    Tools array output has 0 for nulls.
    """
    return garray.array(name, null="nan", env=session.env)


@pytest.mark.parametrize(
    ("direction_format", "suffix"),
    [
        *FORMATS,
        ("power2", "power2"),
        ("auto", "power2"),
        ("taudem", "taudem"),
    ],
)
def test_converging(session, direction_format, suffix):
    """Upstream flow length of all eight directions is the same in each format"""
    tools = Tools(session=session)
    length = tools.r_upflowlength(
        input=f"converging_{suffix}", format=direction_format, output=np.array
    )
    d = 10 * np.sqrt(2)
    expected = [
        [0, 0, 0, 0, 0, 0, 0],
        [d, d, 0, 10, 0, d, d],
        [2 * d, d, 0, 20, 30, 40, 50],
        [d, d, 0, 10, 0, d, d],
        [0, 0, 0, 0, 0, 0, 0],
    ]
    np.testing.assert_allclose(length, expected, rtol=1e-6)


@pytest.mark.parametrize(("direction_format", "suffix"), FORMATS)
def test_east(session, direction_format, suffix):
    """Upstream flow length increases eastward when all cells point East"""
    tools = Tools(session=session)
    length = tools.r_upflowlength(
        input=f"east_{suffix}", format=direction_format, output=np.array
    )
    np.testing.assert_array_equal(length, [list(range(0, 70, 10))] * 5)


def test_null(session):
    """Null directions are null and break the flow path"""
    tools = Tools(session=session)
    tools.r_upflowlength(input="east_null", format="45degree", output="length")
    length = read_with_nulls(session, "length")
    np.testing.assert_array_equal(length, [[0, 10, 20, np.nan, 0, 10, 20]] * 5)
