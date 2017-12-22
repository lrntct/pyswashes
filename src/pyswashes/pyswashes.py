# Copyright 2017 Laurent Courty <laurent@courty.me>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in its version 3.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, os
import shutil
from io import StringIO
import subprocess

import pandas



class SWASHES(object):
    """An interface to a SWASHES analytic solution
    """
    DIMENSION_OK = [1., 1.5, 2.]

    def __init__(self, dimension, stype, domain, choice,
                 num_cell_x, num_cell_y=None, swashes_bin='swashes'):
        # input sanity check
        if float(dimension) not in self.DIMENSION_OK:
            raise ValueError("<dimension> must be in ".format(self.DIMENSION_OK))
        input_int = [stype, domain, choice, num_cell_x]
        if num_cell_y is not None:
           input_int.append(num_cell_y)
        if not all(isinstance(p, int) for p in input_int):
            raise ValueError("<dimension>, <stype>, <domain>, <choice>, "
                             "<num_cell_x>, <num_cell_y> must be integer.")
        if int(dimension) == 2 and not num_cell_y:
            raise ValueError("bidimensional solutions need a positive <num_cell_y>")
        self.params = [dimension] + input_int

        # check if the executable exists
        if not shutil.which(swashes_bin):
            raise RuntimeError("SWASHES executable not found.")
        self.sbin = swashes_bin
        self.out = []
        self._compute()

    def _compute(self):
        """compute an analytic solution.
        Keep the results in a list of lists
        """
        comment_char = '#'
        # convert to str to run the subprocess
        run_cmd = [self.sbin] + [str(p) for p in self.params]
        try:
            proc = subprocess.run(run_cmd, encoding="utf-8",
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  check=True)
        except subprocess.CalledProcessError as cperr:
            cperr_str = ("swashes returned an error: <{}>. "
                         "Calling parameters: {}".format(cperr.stderr.strip(),
                                                         self.params))
            raise RuntimeError(cperr_str)
        else:
            out_lines = proc.stdout.splitlines()
        header_line = None
        for idx, current_line in enumerate(out_lines):
            if idx < (len(out_lines) - 1):
                next_line = out_lines[idx + 1]
            # get the header
            if current_line.startswith(comment_char) and not next_line.startswith(comment_char):
                header_line = current_line.lstrip(comment_char).split()
                self.out.append(header_line)
            # get results
            if not current_line.startswith(comment_char):
                self.out.append(current_line.split())
        return self

    def get_csv(self):
        """return the results as a csv
        """
        csv_lines = []
        for line in self.out:
            csv_lines.append(','.join(line))
        return os.linesep.join(csv_lines)

    def get_dataframe(self):
        """return a pandas DataFrame
        """
        csv = StringIO(self.get_csv())
        return pandas.read_csv(csv, index_col=0)
