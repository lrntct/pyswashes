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
import platform

import pandas


class SWASHES(object):
    """A base class to interface with a SWASHES analytic solution.
    """
    DIMENSION_OK = [1., 1.5, 2.]

    def __init__(self, dimension, stype, domain, choice,
                 num_cell_x, num_cell_y=None, swashes_bin=''):
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

        # set the executable
        self._set_executable(path_to_bin=swashes_bin)

        self.out = []
        # compute the solution
        self._compute()

    def _set_executable(self, path_to_bin=''):
        """
        """
        os = platform.system()
        if path_to_bin:
            self.swashes_bin = path_to_bin
        elif os == 'Windows':
            self.swashes_bin = 'swashes.exe'
        else:
            self.swashes_bin = 'swashes'
        # check if the executable exists
        if not shutil.which(self.swashes_bin):
            raise RuntimeError("SWASHES executable not found: {}"
                               "".format(self.swashes_bin))
        return self

    def _compute(self):
        """compute an analytic solution.
        Keep the results in a list of lists
        """
        comment_char = '#'
        # convert to str to run the subprocess
        run_cmd = [self.swashes_bin] + [str(p) for p in self.params]
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

    def csv(self):
        """return the results as a csv
        """
        csv_lines = []
        for line in self.out:
            csv_lines.append(','.join(line))
        return os.linesep.join(csv_lines)

    def dataframe(self):
        """return a pandas DataFrame
        """
        csv_file = StringIO(self.csv())
        return pandas.read_csv(csv_file, index_col=0)


class OneDimensional(SWASHES):
    """an interface to one-dimensional solutions
    """
    def __init__(self, stype, domain, choice, num_cell_x):
        SWASHES.__init__(self, 1., stype, domain, choice, num_cell_x)


class PseudoTwoDimensional(SWASHES):
    """an interface to pseudo two-dimensional solutions
    """
    def __init__(self, stype, domain, choice, num_cell_x):
        SWASHES.__init__(self, 1.5, stype, domain, choice, num_cell_x)


class TwoDimensional(SWASHES):
    """an interface to two-dimensional solutions
    """
    def __init__(self, stype, domain, choice, num_cell_x, num_cell_y):
        SWASHES.__init__(self, 2., stype, domain, choice, num_cell_x, num_cell_y)

    def dataframe(self):
        """return a pandas DataFrame.
        Two indices because it's 2D.
        """
        csv = StringIO(self.csv())
        return pandas.read_csv(csv, index_col=[0,1])
