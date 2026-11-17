"""Tests of r.lfp.

SPDX-FileCopyrightText: 2026 Vaclav Petras
SPDX-License-Identifier: GPL-2.0-or-later
"""

import re

import pytest

from grass.tools import Tools

# Several threads give wrong paths in debug builds because of a data race
# (shared inner loop counter in lfp_funcs.h).
NPROCS = 1
FORMATS = [
    ("45degree", "45degree"),
    ("degree", "degree"),
    ("auto", "degree"),
]
# Each outlet of converging_outlets has two equally long paths, one from the
# north edge and one from the south edge.
CONVERGING_PATHS = sorted(
    [
        ((2.5, 4.5), (1.5, 3.5), (0.5, 3.5), (0.5, 2.5)),
        ((2.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 2.5)),
        ((3.5, 4.5), (4.5, 3.5), (5.5, 3.5), (6.5, 2.5)),
        ((3.5, 0.5), (4.5, 1.5), (5.5, 1.5), (6.5, 2.5)),
    ]
)


def flow_paths(tools, name):
    """Lines of a vector map as a sorted list of tuples of (x, y) vertices

    The vertices go from upstream to the outlet (current implementation,
    not documented).
    """
    paths = []
    for line in tools.v_out_ascii(input=name, format="wkt").text.splitlines():
        match = re.fullmatch(r"LINESTRING\((.+)\)", line)
        assert match, f"Not a LINESTRING: {line!r}"
        paths.append(
            tuple(
                tuple(float(c) for c in vertex.split())
                for vertex in match[1].split(",")
            )
        )
    return sorted(paths)


@pytest.mark.parametrize(
    ("direction_format", "suffix"),
    [
        *FORMATS,
        ("auto", "45degree"),
        ("power2", "power2"),
        ("auto", "power2"),
        ("taudem", "taudem"),
    ],
)
def test_converging(session, direction_format, suffix):
    """Longest flow paths of all eight directions are the same in each format"""
    tools = Tools(session=session, overwrite=True)
    tools.r_lfp(
        direction=f"converging_{suffix}",
        format=direction_format,
        outlets="converging_outlets",
        lfp="lfp",
        nprocs=NPROCS,
    )
    assert flow_paths(tools, "lfp") == CONVERGING_PATHS


def test_custom(session):
    """Custom encoding of the 45degree format gives the same longest flow paths"""
    tools = Tools(session=session, overwrite=True)
    # The trailing underscore avoids a clash with Popen's encoding parameter.
    tools.r_lfp(
        direction="converging_45degree",
        format="custom",
        encoding_="8,7,6,5,4,3,2,1",
        outlets="converging_outlets",
        lfp="lfp",
        nprocs=NPROCS,
    )
    assert flow_paths(tools, "lfp") == CONVERGING_PATHS


@pytest.mark.parametrize(("direction_format", "suffix"), FORMATS)
def test_east(session, direction_format, suffix):
    """The longest flow path is the whole row when all cells point East"""
    tools = Tools(session=session, overwrite=True)
    tools.r_lfp(
        direction=f"east_{suffix}",
        format=direction_format,
        outlets="east_outlet",
        lfp="lfp",
        nprocs=NPROCS,
    )
    assert flow_paths(tools, "lfp") == [tuple((x + 0.5, 2.5) for x in range(7))]


@pytest.mark.parametrize(
    ("direction_format", "direction"),
    [
        ("45degree", "east_null"),
        ("45degree", "east_zero_45degree"),
        ("degree", "east_zero_degree"),
        ("degree", "east_30_degree"),
    ],
)
def test_no_direction(session, direction_format, direction):
    """Cells without a direction break the flow path"""
    tools = Tools(session=session, overwrite=True)
    tools.r_lfp(
        direction=direction,
        format=direction_format,
        outlets="east_outlet",
        lfp="lfp",
        nprocs=NPROCS,
    )
    assert flow_paths(tools, "lfp") == [((4.5, 2.5), (5.5, 2.5), (6.5, 2.5))]
