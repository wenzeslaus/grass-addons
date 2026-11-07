"""Fixtures for the r.hydrobasin tests.

SPDX-FileCopyrightText: 2026 Vaclav Petras
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os
from io import StringIO

import pytest

import grass.script as gs
from grass.tools import Tools

# Directions in the 45degree format (1=NE, 2=N, ..., 8=E). The three west
# columns drain to the cell in row 3 on the west edge, the four east columns
# to the cell in row 3 on the east edge, and the grid uses all eight
# directions.
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
    """Session in a 5x7 XY project with direction rasters and outlets.

    The rasters converging_45degree, converging_degree, and
    converging_power2 have the same directions in different formats.
    In east_45degree and east_degree, all cells point East, with negative
    values in the east edge column as in r.watershed. In east_zero_45degree,
    east_zero_degree, and east_30_degree, all cells point East except for
    column 4, which has a value meaning no direction (0, 0, and 30).
    In too_low_degree and too_low_45degree, the west edge column is below
    the valid range of the format.

    The outlets of converging_outlets are the west edge (category 1) and
    east edge (category 2) cells of row 3, those of east_outlets are the
    east edge cells of rows 1 to 5 (categories 1 to 5). The outlets of
    nested_outlets are the cells in columns 4 (category 1, id 10) and 7
    (category 2, id 20) of row 3.
    """
    project = tmp_path_factory.mktemp("r_hydrobasin") / "project"
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
            tools.r_mapcalc(expression="east_zero_45degree = if(col() == 4, 0, 8)")
            tools.r_mapcalc(expression="east_zero_degree = if(col() == 4, 0, 360)")
            tools.r_mapcalc(expression="east_30_degree = if(col() == 4, 30, 360)")
            tools.r_mapcalc(expression="too_low_degree = if(col() == 1, -405, 360)")
            tools.r_mapcalc(expression="too_low_45degree = if(col() == 1, -9, 8)")
            tools.v_in_ascii(
                input=StringIO("0.5|2.5\n6.5|2.5\n"), output="converging_outlets"
            )
            tools.v_in_ascii(
                input=StringIO("6.5|4.5\n6.5|3.5\n6.5|2.5\n6.5|1.5\n6.5|0.5\n"),
                output="east_outlets",
            )
            tools.v_in_ascii(
                input=StringIO("3.5|2.5|10\n6.5|2.5|20\n"),
                output="nested_outlets",
                columns="x double precision, y double precision, id integer",
            )
            yield session
