"""Fixtures for the r.flowaccumulation tests.

SPDX-FileCopyrightText: 2026 Vaclav Petras
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os
from io import StringIO

import pytest

import grass.script as gs
from grass.tools import Tools

# Directions in the 45degree format (1=NE, 2=N, ..., 8=E). Columns 1-3
# drain to the cell in row 3 on the west edge, columns 4-7 to the cell in
# row 3 on the east edge, and the grid uses all eight directions.
CONVERGING_45DEGREE = """\
north: 5
south: 0
east: 7
west: 0
rows: 5
cols: 7
6 5 5 6 7 7 6
6 5 5 6 7 7 6
4 4 4 8 8 8 8
2 3 3 2 1 1 2
2 3 3 2 1 1 2
"""


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    """Session in a 5x7 XY project with direction and weight rasters.

    The rasters converging_45degree, converging_degree, and
    converging_power2 have the same directions in different formats.
    In east_45degree and east_degree, all cells point East, with negative
    values in the east edge column as in r.watershed. In east_null, all
    cells point East except for null cells in column 4. In
    east_invalid_power2, all cells point East except for an invalid code
    in column 4. The weight raster col_weight is the column number,
    null_weight is the same with null cells in column 4.
    """
    project = tmp_path_factory.mktemp("r_flowaccumulation") / "project"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        with Tools(session=session) as tools:
            tools.g_region(n=5, s=0, e=7, w=0, res=1)
            tools.r_in_ascii(
                input=StringIO(CONVERGING_45DEGREE), output="converging_45degree"
            )
            tools.r_mapcalc(expression="converging_degree = 45 * converging_45degree")
            tools.r_mapcalc(
                expression="converging_power2 = int(exp(2, 8 - converging_45degree))"
            )
            tools.r_mapcalc(expression="east_45degree = if(col() == 7, -8, 8)")
            tools.r_mapcalc(expression="east_degree = if(col() == 7, -360, 360)")
            tools.r_mapcalc(expression="east_null = if(col() == 4, null(), 8)")
            # Power2 code 3 is not a valid direction.
            tools.r_mapcalc(expression="east_invalid_power2 = if(col() == 4, 3, 1)")
            tools.r_mapcalc(expression="col_weight = col()")
            tools.r_mapcalc(expression="null_weight = if(col() == 4, null(), col())")
            yield session


@pytest.fixture(scope="module")
def long_path_session(tmp_path_factory):
    """Session in a 660x660 XY project with a single long flow path.

    In long_path_45degree, odd rows flow East and even rows flow West, and
    the cells at the end of each row flow South, so the path snakes through
    all cells, row by row, and leaves the region at the south-west corner.
    """
    project = tmp_path_factory.mktemp("r_flowaccumulation_long_path") / "project"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        with Tools(session=session) as tools:
            # Long enough to overflow the stack if tracing recurses once per cell.
            size = 660
            tools.g_region(n=size, s=0, e=size, w=0, res=1)
            tools.r_mapcalc(
                expression=(
                    "long_path_45degree = "
                    f"if(row() % 2, if(col() == {size}, 6, 8), if(col() == 1, 6, 4))"
                )
            )
            yield session
