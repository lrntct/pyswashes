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
from io import StringIO
import subprocess

import pandas

class SWASHES(object):
    """An interface to a SWASHES analytic solution
    """
    def __init__(self, swashes_bin, dimension, stype, domain, choice,
                 NumberCellx, NumberCelly=None):
        self.sbin = swashes_bin
        self.params = [str(dimension), str(stype), str(domain),
                       str(choice), str(NumberCellx)]
        if NumberCelly is not None:
            self.params.append(NumberCelly)
        self.out = []

    def compute(self):
        """compute an analytic solution.
        Keep the results in a list of lists
        """
        comment_char = '#'
        proc = subprocess.run([self.sbin]+self.params, encoding="utf-8",
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.stderr:
            sys.exit(proc.stderr.strip())
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
