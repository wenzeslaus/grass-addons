"""Fixtures for the r.lfp tests.

SPDX-FileCopyrightText: 2026 Vaclav Petras
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os
from io import StringIO

import pytest

import grass.script as gs
from grass.tools import Tools

# Directions in the 45degree format (1=NE, 2=N, ..., 8=E). The cells drain
# to the west edge cell or the east edge cell of row 3, and the longest flow
# paths to these two cells together use all eight directions.
CONVERGING_45DEGREE = """\
north: 5
south: 0
east: 7
west: 0
rows: 5
cols: 7
6 5 5 7 7 6 6
6 4 5 7 8 7 6
4 4 4 8 8 8 8
2 4 3 1 8 1 2
2 3 3 1 1 2 2
"""


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    """Session in a 5x7 XY project with direction rasters and outlets.

    The rasters converging_45degree, converging_degree, converging_power2,
    and converging_taudem have the same directions in different formats.
    In east_45degree and east_degree, all cells point East, with negative
    values in the east edge column as in r.watershed. In east_null, all
    cells point East except for null cells in column 4.

    The outlets of converging_outlets are the west edge and east edge cells
    of row 3, east_outlet is only the east edge cell of row 3.
    """
    project = tmp_path_factory.mktemp("r_lfp") / "project"
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
            tools.r_mapcalc(
                expression="converging_taudem = converging_45degree % 8 + 1"
            )
            tools.r_mapcalc(expression="east_45degree = if(col() == 7, -8, 8)")
            tools.r_mapcalc(expression="east_degree = if(col() == 7, -360, 360)")
            tools.r_mapcalc(expression="east_null = if(col() == 4, null(), 8)")
            tools.v_in_ascii(
                input=StringIO("0.5|2.5\n6.5|2.5\n"), output="converging_outlets"
            )
            tools.v_in_ascii(input=StringIO("6.5|2.5\n"), output="east_outlet")
            yield session
