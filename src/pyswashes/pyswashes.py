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

import pandas as pd
import numpy as np


# columns names
X = 'x'
Y = 'y'
DEPTH = 'depth'
HEAD = 'head'
CRIT_HEAD = 'crit_head'
VEL1D = 'u'
VEL_X = 'u'  # solution.cpp: u, flow velocity in x
VEL_Y = 'v'  # solution.cpp: v, flow velocity in y
VEL2D = 'U'  # velocity norm
GD_ELEVATION = 'gd_elev'
FLOW = 'q'
FLOW_X = 'qx'
FLOW_Y = 'qy'
FROUDE = 'Froude'


class SWASHES(object):
    """A base class to interface with a SWASHES analytic solution.
    """
    DIMENSION_OK = [1., 1.5, 2.]
    COLS = {'(i-0.5)*dx': X, 'h[i]': DEPTH, 'u[i]': VEL1D,
            'topo[i]': GD_ELEVATION, 'q[i]': FLOW, 'topo[i]+h[i]': HEAD,
            'Fr[i]=Froude': FROUDE, 'topo[i]+hc[i]': CRIT_HEAD}

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

        # parameters of the domain
        self.dom_params = {'length': None, 'width': None,
                           'dx': None, 'dy': None,
                           'ncellx': None, 'ncelly': None}

        # value to replace nan with in ascii grid raster
        self.nan_val = -99999
        self.generated_by = None
        self.results = []
        self.raw_comments = []
        # compute the solution
        self._compute()._read_output()._read_comments()

    @staticmethod
    def get_number_from_str(string):
        """get a parameter string from the swashes comments
        return the float after ':' and before trailing space
        """
        param_val_raw = string.strip().rpartition(':')[2].strip()
        return float(param_val_raw.split()[0].strip())

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
            self.raw_output = proc.stdout
        return self

    def _read_output(self):
        c_char = '#'
        out_lines = self.raw_output.splitlines()
        for idx, current_line in enumerate(out_lines):
            if idx < (len(out_lines) - 1):
                next_line = out_lines[idx + 1]
            # comments
            if current_line.startswith(c_char) and next_line.startswith(c_char):
                self.raw_comments.append(current_line.lstrip(c_char).strip())
            # get the columns headers
            if current_line.startswith(c_char) and not next_line.startswith(c_char):
                raw_col_headers = current_line.lstrip(c_char).split()
                col_headers = [self.COLS[h] for h in raw_col_headers]
                self.results.append(col_headers)
            # get results
            if not current_line.startswith(c_char):
                self.results.append(current_line.split())
        return self

    def _read_comments(self):
        """extract values from the solution's comments
        """
        DIM = 'Dimension:'
        STYPE = 'Type:'
        DOMAIN = 'Domain:'
        CHOICE = 'Choice:'

        sol_param_keys = {'length': ['Length of the domain:'],
                          'width': ['Width of the domain:'],
                          'dx': ['Space step in x:', 'Space step:'],
                          'dy': ['Space step in y:'],
                          'ncellx': ['Number of cells in x:',
                                     'Number of cells:'],
                          'ncelly': ['Number of cells in y:']
                          }

        for current_line in self.raw_comments:
            if not current_line:
                continue
            # generated by
            if current_line.startswith("Generated by"):
                self.generated_by = current_line.strip()
            # Make sure the solution type is coherent
            for idx, param in enumerate([DIM, STYPE, DOMAIN, CHOICE]):
                if current_line.startswith(param):
                    param_val = self.get_number_from_str(current_line)
                    assert param_val == float(self.params[idx])
            # parameters of the solution
            for key, keywords in sol_param_keys.items():
                for keyword in keywords:
                    if current_line.startswith(keyword):
                        self.dom_params[key] = self.get_number_from_str(current_line)
        # Verify domain parameters
        assert self.dom_params['ncellx'] == float(self.params[4])
        if self.dom_params['ncelly'] is not None:
            assert self.dom_params['ncelly'] == float(self.params[5])
        return self

    def csv(self):
        """return the results as a csv
        """
        csv_lines = []
        for line in self.results:
            csv_lines.append(','.join(line))
        return os.linesep.join(csv_lines)

    def dataframe(self):
        """return a pandas DataFrame
        """
        csv_file = StringIO(self.csv())
        return pd.read_csv(csv_file, index_col=0)

    def np_array(self, value):
        """return a numpy ndarray of the given value
        """
        df = self.dataframe()
        ndarray = df[value].values
        assert ndarray.ndim in [1, 2]
        return ndarray

    def np_topo(self):
        """return a numpy array of the topography
        """
        return self.np_array(GD_ELEVATION)

    def np_depth(self):
        """return a numpy array of the topography
        """
        return self.np_array(DEPTH)


class OneDimensional(SWASHES):
    """an interface to one-dimensional solutions
    """
    def __init__(self, stype, domain, choice, num_cell_x):
        SWASHES.__init__(self, 1., stype, domain, choice, num_cell_x)

    def ascii_grid(self, value, filename, nrows=3):
        """write an ascii grid string of the given value
        pad the array to nrows
        """
        # get the numpy array and replace nan
        arr = self.np_array(value)
        arr[np.isnan(arr)] = self.nan_val
        # add dimension and pad
        if arr.ndim == 1:
            arr = arr[np.newaxis]
            arr = np.pad(arr, ((nrows-1, 0), (0,0)), mode='edge')
            assert nrows == arr.shape[0]
            assert int(self.dom_params['ncellx']) == arr.shape[1]
        else:
            raise RuntimeError("Expected one-dimensional array")
        # header
        ncols = "NCOLS {}\n".format(int(self.dom_params['ncellx']))
        nrows = "NROWS {}\n".format(int(nrows))
        xll = "XLLCORNER 0.0\nYLLCORNER 0.0\n"  # coordinates origin to 0
        # in one-dimensions, cells are squared
        dx = "CELLSIZE {}\n".format(self.dom_params['dx'])
        nodata = "NODATA_VALUE {}\n".format(self.nan_val)
        header = ncols + nrows + xll + dx + nodata
        # writing file
        np.savetxt(filename, arr, fmt='%.6f',
                   header=header, comments='')
        return self


class PseudoTwoDimensional(SWASHES):
    """an interface to pseudo two-dimensional solutions
    """
    def __init__(self, stype, domain, choice, num_cell_x):
        SWASHES.__init__(self, 1.5, stype, domain, choice, num_cell_x)


class TwoDimensional(SWASHES):
    """an interface to two-dimensional solutions
    """

    COLS = {'(i-0.5)*dx': X, '(j-0.5)*dy': Y, 'h[i][j]': DEPTH,
            'u[i][j]': VEL_X, 'v[i][j]': VEL_Y,
            'topo[i][j]+h[i][j]': HEAD, 'topo[i][j]': GD_ELEVATION,
            '||U||[i][j]': VEL2D, 'Fr[i][j]': FROUDE,
            'qx[i][j]': FLOW_X, 'qy[i][j]': FLOW_Y, 'q[i][j]': FLOW}

    def __init__(self, stype, domain, choice, num_cell_x, num_cell_y):
        SWASHES.__init__(self, 2., stype, domain, choice, num_cell_x, num_cell_y)

    def dataframe(self):
        """return a pandas DataFrame.
        Two indices because it's 2D.
        """
        csv = StringIO(self.csv())
        return pd.read_csv(csv, index_col=[0,1])

    def np_array(self, value):
        """return a numpy array of the given value
        """
        # return the indices as columns
        df = self.dataframe().reset_index(drop=False)
        # pivot and get the values as a numpy ndarray
        return df.pivot(index=Y, columns=X, values=value).values

    def ascii_grid(self, value, filename):
        """write an ascii grid string of the given value
        """
        # get the numpy array and replace nan
        ndarr = self.np_array(value)
        ndarr[np.isnan(ndarr)] = self.nan_val
        # header
        assert int(self.dom_params['ncellx']) == ndarr.shape[1]
        assert int(self.dom_params['ncelly']) == ndarr.shape[0]
        ncols = "NCOLS {}\n".format(int(self.dom_params['ncellx']))
        nrows = "NROWS {}\n".format(int(self.dom_params['ncelly']))
        xll = "XLLCORNER 0.0\nYLLCORNER 0.0\n"  # no coordinates
        dx = "DX {}\n".format(self.dom_params['dx'])
        dy = "DY {}\n".format(self.dom_params['dy'])
        nodata = "NODATA_VALUE {}\n".format(self.nan_val)
        header = ncols + nrows + xll + dx + dy + nodata
        # writing file
        np.savetxt(filename, ndarr, fmt='%.6f',
                   header=header, comments='')
        return self
