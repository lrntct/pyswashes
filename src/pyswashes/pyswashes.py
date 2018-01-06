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

"""An interface to the SWASHES software,
a collection of analytic solutions to the shallow water equations.
"""

import os
import shutil
from io import StringIO
import subprocess
import platform

import pandas as pd
import numpy as np


# Pandas columns names
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
    """
    A base class that interfaces with a SWASHES analytic solution.

    Please use `OneDimensional`, `PseudoTwoDimensional`
    and `TwoDimensional` for normal use, as they overload some methods of the base class.

    Parameters
    ----------
    dimension : float
        Dimension of the solution. Either 1., 1.5 or 2.
    stype : int
        The type of the solution.
    domain : int
        The domain of the solution.
    choice : int
        The choice of solution.
    num_cell_x : int
        The number of cells in the X dimension.
    num_cell_y : int, optional
        The number of cells in the Y dimension.
    swashes_bin : str, optional
        Path to the SWASHES executable.
        Only needed if swashes is not in your PATH.
        Default to an empty string, which triggers the setting of
        the path to 'swashes' or 'swashes.exe',
        according to the platform.

    Attributes
    ----------
    dom_params : dictionary
        The parameters of the domain.

    Raises
    ------
    ValueError
        If the parameters are the wrong type.
    ValueError
        If `num_cell_y` is not given for a 2D solution.
    RuntimeError
        If the SWASHES executable is not found
    RuntimeError
        When SWASHES returns an error
    """

    DIMENSION_OK = [1., 1.5, 2.]
    COLS = {'(i-0.5)*dx': X, 'h[i]': DEPTH, 'u[i]': VEL1D,
            'topo[i]': GD_ELEVATION, 'q[i]': FLOW, 'topo[i]+h[i]': HEAD,
            'Fr[i]=Froude': FROUDE, 'topo[i]+hc[i]': CRIT_HEAD}

    def __init__(self, dimension, stype, domain, choice,
                 num_cell_x, num_cell_y=None, swashes_bin=''):
        # input sanity check
        if float(dimension) not in self.DIMENSION_OK:
            raise ValueError("<dimension> must be in {}".format(self.DIMENSION_OK))
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
        """Set the path to the SWASHES executable according to the platform.
        Assumes it is in the PATH.
        """
        os_name = platform.system()
        if path_to_bin:
            self.swashes_bin = path_to_bin
        elif os_name == 'Windows':
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
        """
        Read the raw text output and populate the internal results list.
        """
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
        """Extract values from the solution's comments.
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

    def cols(self):
        """Return a list of the available values.

        Returns
        -------
        list of strings

        Examples
        --------
        >>> import pyswashes
        >>> unidim = pyswashes.OneDimensional(2,1,2,6)
        >>> print(unidim.cols())
        ['x', 'depth', 'u', 'gd_elev', 'q', 'head', 'Froude', 'crit_head']

        >>> pseudo2d = pyswashes.PseudoTwoDimensional(1,1,1,5)
        >>> print(pseudo2d.cols())
        ['x', 'depth', 'gd_elev', 'head']
        """
        return self.results[0]

    def csv(self):
        """Return the solution results as a CSV string.

        Returns
        -------
        str
            Values are separated by a comma.
            Lines are separated by an OS specific line separator.

        Examples
        --------

        >>> import pyswashes
        >>> unidim = pyswashes.OneDimensional(2, 1, 2, 5)
        >>> print(unidim.csv())
        x,depth,u,gd_elev,q,head,Froude,crit_head
        100,0.770195,2.59675,5.88374,2,6.65393,0.944702,6.62527
        300,0.937035,2.13439,4.67542,2,5.61245,0.703982,5.41695
        500,1.1123,1.79808,4.06441,2,5.17671,0.544331,4.80595
        700,0.937035,2.13439,3.10854,2,4.04558,0.703982,3.85008
        900,0.770195,2.59675,1.03618,2,1.80638,0.944702,1.77771

        >>> pseudo2d = pyswashes.PseudoTwoDimensional(1, 1, 1, 5)
        >>> print(pseudo2d.csv())
        x,depth,gd_elev,head
        20,0.912229,1.64477,2.55699
        60,1.0348,0.844012,1.87881
        100,1.2,0.314957,1.51496
        140,1.0348,0.281316,1.31611
        180,0.912229,0.093772,1.006

        >>> twod = pyswashes.TwoDimensional(1,1,1,50,50)
        >>> print(twod.csv())
        x,y,depth,u,v,head,gd_elev,U,Froude,qx,qy,q
        ...
        2.84,1.64,0.0,0.0,0.0,-0.01648,-0.01648,0.0,NaN,0.0,0.0,0.0
        2.84,1.72,0.0025,-7.12758e-09,2.37586e-09,-0.0191,-0.0216,7.51313e-09,4.79751e-08,-1.78189e-11,5.93965e-12,1.87828e-11
        2.84,1.8,0.0085,-7.12758e-09,1.69704e-09,-0.01694,-0.02544,7.32682e-09,2.5373e-08,-6.05844e-11,1.44249e-11,6.2278e-11
        2.84,1.88,0.0125,-7.12758e-09,1.01823e-09,-0.0155,-0.028,7.19994e-09,2.05608e-08,-8.90947e-11,1.27278e-11,8.99993e-11
        2.84,1.96,0.0145,-7.12758e-09,3.39408e-10,-0.01478,-0.02928,7.13565e-09,1.89197e-08,-1.0335e-10,4.92142e-12,1.03467e-10
        2.84,2.04,0.0145,-7.12758e-09,-3.39408e-10,-0.01478,-0.02928,7.13565e-09,1.89197e-08,-1.0335e-10,-4.92142e-12,1.03467e-10
        2.84,2.12,0.0125,-7.12758e-09,-1.01823e-09,-0.0155,-0.028,7.19994e-09,2.05608e-08,-8.90947e-11,-1.27278e-11,8.99993e-11
        2.84,2.2,0.0085,-7.12758e-09,-1.69704e-09,-0.01694,-0.02544,7.32682e-09,2.5373e-08,-6.05844e-11,-1.44249e-11,6.2278e-11
        2.84,2.28,0.0025,-7.12758e-09,-2.37586e-09,-0.0191,-0.0216,7.51313e-09,4.79751e-08,-1.78189e-11,-5.93965e-12,1.87828e-11
        2.84,2.36,0.0,0.0,0.0,-0.01648,-0.01648,0.0,NaN,0.0,0.0,0.0
        ...
        """
        csv_lines = []
        for line in self.results:
            csv_lines.append(','.join(line))
        return os.linesep.join(csv_lines)

    def dataframe(self):
        """Return the solution results as a Pandas DataFrame.

        Returns
        -------
        Pandas dataframe
            The X in meters is the index.

        Examples
        --------

        >>> import pyswashes

        >>> unidim = pyswashes.OneDimensional(2, 1, 2, 5)
        >>> print(unidim.dataframe())
                depth        u  gd_elev  q     head    Froude  crit_head
        x                                                               
        100  0.770195  2.59675  5.88374  2  6.65393  0.944702    6.62527
        300  0.937035  2.13439  4.67542  2  5.61245  0.703982    5.41695
        500  1.112300  1.79808  4.06441  2  5.17671  0.544331    4.80595
        700  0.937035  2.13439  3.10854  2  4.04558  0.703982    3.85008
        900  0.770195  2.59675  1.03618  2  1.80638  0.944702    1.77771

        >>> pseudo2d = pyswashes.PseudoTwoDimensional(1, 1, 1, 5)
        >>> print(pseudo2d.dataframe())
                depth   gd_elev     head
        x                               
        20   0.912229  1.644770  2.55699
        60   1.034800  0.844012  1.87881
        100  1.200000  0.314957  1.51496
        140  1.034800  0.281316  1.31611
        180  0.912229  0.093772  1.00600
        """
        csv_file = StringIO(self.csv())
        return pd.read_csv(csv_file, index_col=0)

    def np_array(self, value):
        """Return a NumPy ndarray of the given value.

        Parameters
        ----------
        value : str
            A value from `cols()`.

        Returns
        -------
        NumPy ndarray

        Examples
        --------

        >>> import pyswashes
        >>> unidim = pyswashes.OneDimensional(2,1,2,6)
        >>> print(unidim.np_array('depth'))
        [ 0.764586  0.87793   1.07331   1.07331   0.87793   0.764586]

        >>> pseudo2d = pyswashes.PseudoTwoDimensional(1,1,1,5)
        >>> print(pseudo2d.np_array('depth'))
        [ 0.912229  1.0348    1.2       1.0348    0.912229]

        Raises
        ------
        ValueError
            If `value` is not in `cols()`
        """
        if value not in self.cols():
            raise ValueError("<value> must be in {}".format(self.cols()))
        df = self.dataframe()
        ndarray = df[value].values
        assert ndarray.ndim in [1, 2]
        return ndarray

    def np_topo(self):
        """Return a NumPy array of the topography (i.e, ground elevation).
        It is a shortcut to `np_array()`.

        Returns
        -------
        NumPy ndarray

        Examples
        --------

        >>> import pyswashes
        >>> unidim = pyswashes.OneDimensional(2,1,2,6)
        >>> print(unidim.np_topo())
        [ 6.04563   4.85287   4.18056   3.70591   2.65771   0.885902]

        >>> pseudo2d = pyswashes.PseudoTwoDimensional(1,1,1,5)
        >>> print(pseudo2d.np_topo())
        [ 1.64477   0.844012  0.314957  0.281316  0.093772]


        It is equivalent to calling `np_array()` with the adequate `value` parameter:

        >>> unidim.np_topo().all() == unidim.np_array(value=pyswashes.pyswashes.GD_ELEVATION).all()
        True
        """
        return self.np_array(GD_ELEVATION)

    def np_depth(self):
        """Return a numpy array of the water depth.
        It is a shortcut to `np_array()`.

        Returns
        -------
        NumPy ndarray

        Examples
        --------

        >>> import pyswashes
        >>> unidim = pyswashes.OneDimensional(2,1,2,6)
        >>> print(unidim.np_depth())
        [ 0.764586  0.87793   1.07331   1.07331   0.87793   0.764586]

        >>> pseudo2d = pyswashes.PseudoTwoDimensional(1,1,1,5)
        >>> print(pseudo2d.np_depth())
        [ 0.912229  1.0348    1.2       1.0348    0.912229]

        It is equivalent to calling `np_array()` with the adequate `value` parameter:

        >>> unidim.np_depth().all() == unidim.np_array(value=pyswashes.pyswashes.DEPTH).all()
        True
        """
        return self.np_array(DEPTH)


class OneDimensional(SWASHES):
    """A one-dimensional analytic solution.

    To select `stype`, `domain` and `choice`,
    please refer to the SWASHES manual.

    Parameters
    ----------
    stype : int
        The type of the solution.
    domain : int
        The domain of the solution.
    choice : int
        The choice of solution.
    num_cell_x : int
        The number of cells in the X dimension.
    swashes_bin : str, optional
        Path to the SWASHES executable.
        Only needed if swashes is not in your PATH.
        Default to an empty string, which triggers the setting of
        the path to 'swashes' or 'swashes.exe',
        according to the platform.

    Attributes
    ----------
    dom_params : dictionary
        The paramters of the domain.

    Examples
    --------

    Get the solution of a MacDonald Long channel without rain,
    with a 5 cells discretization:

    >>> import pyswashes
    >>> s = pyswashes.OneDimensional(2, 1, 2, 5)

    Report the solution's domain pramaters:

    >>> print(s.dom_params)
    {'length': 1000.0, 'width': None, 'dx': 200.0, 'dy': None, 'ncellx': 5.0, 'ncelly': None}

    Get a Pandas dataframe:

    >>> print(s.dataframe())
            depth        u  gd_elev  q     head    Froude  crit_head
    x                                                               
    100  0.770195  2.59675  5.88374  2  6.65393  0.944702    6.62527
    300  0.937035  2.13439  4.67542  2  5.61245  0.703982    5.41695
    500  1.112300  1.79808  4.06441  2  5.17671  0.544331    4.80595
    700  0.937035  2.13439  3.10854  2  4.04558  0.703982    3.85008
    900  0.770195  2.59675  1.03618  2  1.80638  0.944702    1.77771

    Raises
    ------
    ValueError
        If the parameters are the wrong type.
    ValueError
        If `num_cell_y` is not given for a 2D solution.
    RuntimeError
        If the SWASHES executable is not found
    RuntimeError
        When the SWASHES call returns an error
    """
    def __init__(self, stype, domain, choice, num_cell_x, swashes_bin=''):
        SWASHES.__init__(self, 1., stype, domain, choice, num_cell_x,
                         swashes_bin=swashes_bin)

    def ascii_grid(self, value, filename, nrows=3):
        """Write an ascii grid GIS file.

        The lowest left corner is set to the coordinates 0,0.

        Parameters
        ----------
        value : str
            A value from `cols()`.
        filename : str
            Path to the file to write.
        nrows : int, optional
            The minimum number of rows in the output file.
            Default to 3.

        Examples
        --------

        >>> import pyswashes
        >>> macdonald = pyswashes.OneDimensional(2,1,2,5)
        >>> macdonald.ascii_grid('depth', 'test.asc')
        >>> with open('test.asc', 'r') as test_file:
        ...     for l in test_file:
        ...             print(l.strip())
        ... 
        NCOLS 5
        NROWS 3
        XLLCORNER 0.0
        YLLCORNER 0.0
        CELLSIZE 200.0
        NODATA_VALUE -99999
        <BLANKLINE>
        0.770195 0.937035 1.112300 0.937035 0.770195
        0.770195 0.937035 1.112300 0.937035 0.770195
        0.770195 0.937035 1.112300 0.937035 0.770195
        """
        # get the numpy array and replace nan
        arr = self.np_array(value)
        arr[np.isnan(arr)] = self.nan_val
        # add dimension and pad
        if arr.ndim == 1:
            arr = arr[np.newaxis]
            arr = np.pad(arr, ((nrows-1, 0), (0, 0)), mode='edge')
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


class PseudoTwoDimensional(SWASHES):
    """A pseudo two-dimensional analytic solution.

    To select `stype`, `domain` and `choice`,
    please refer to the SWASHES manual.

    Parameters
    ----------
    stype : int
        The type of the solution.
    domain : int
        The domain of the solution.
    choice : int
        The choice of solution.
    num_cell_x : int
        The number of cells in the X dimension.
    swashes_bin : str, optional
        Path to the SWASHES executable.
        Only needed if swashes is not in your PATH.
        Default to an empty string, which triggers the setting of
        the path to 'swashes' or 'swashes.exe',
        according to the platform.

    Attributes
    ----------
    dom_params : dictionary
        The paramters of the domain.

    Examples
    --------

    Get a MacDonald pseudo 2D with Rectangular short channel,
    subcritical flow, discretized with five cells:

    >>> import pyswashes
    >>> s = pyswashes.PseudoTwoDimensional(1, 1, 1, 5)

    Report the solution's domain pramaters:

    >>> print(s.dom_params)
    {'length': 200.0, 'width': None, 'dx': 40.0, 'dy': None, 'ncellx': 5.0, 'ncelly': None}

    Get a Pandas dataframe:

    >>> print(s.dataframe())
            depth   gd_elev     head
    x                               
    20   0.912229  1.644770  2.55699
    60   1.034800  0.844012  1.87881
    100  1.200000  0.314957  1.51496
    140  1.034800  0.281316  1.31611
    180  0.912229  0.093772  1.00600


    Raises
    ------
    ValueError
        If the parameters are the wrong type.
    ValueError
        If `num_cell_y` is not given for a 2D solution.
    RuntimeError
        If the SWASHES executable is not found
    RuntimeError
        When the SWASHES call returns an error
    """
    def __init__(self, stype, domain, choice, num_cell_x, swashes_bin=''):
        SWASHES.__init__(self, 1.5, stype, domain, choice, num_cell_x,
                         swashes_bin=swashes_bin)


class TwoDimensional(SWASHES):
    """A two-dimensional analytic solution.

    To select `stype`, `domain` and `choice`,
    please refer to the SWASHES manual.

    Parameters
    ----------
    stype : int
        The type of the solution.
    domain : int
        The domain of the solution.
    choice : int
        The choice of solution.
    num_cell_x : int
        The number of cells in the X dimension.
    num_cell_y : int
        The number of cells in the X dimension.
    swashes_bin : str, optional
        Path to the SWASHES executable.
        Only needed if swashes is not in your PATH.
        Default to an empty string, which triggers the setting of
        the path to 'swashes' or 'swashes.exe',
        according to the platform.

    Attributes
    ----------
    dom_params : dictionary
        The paramters of the domain.

    Examples
    --------

    Get a radially-symmetrical paraboloid (Thacker's solution),
    discretized with 5x5 cells:

    >>> import pyswashes
    >>> s = pyswashes.TwoDimensional(1, 1, 1, 5, 5)

    Report the solution's domain pramaters:

    >>> print(s.dom_params)
    {'length': 4.0, 'width': 4.0, 'dx': 0.8, 'dy': 0.8, 'ncellx': 5.0, 'ncelly': 5.0}

    Get a NumPy array of the ground elevation:

    >>> print(s.np_topo())
    [[ 0.412  0.22   0.156  0.22   0.412]
     [ 0.22   0.028 -0.036  0.028  0.22 ]
     [ 0.156 -0.036 -0.1   -0.036  0.156]
     [ 0.22   0.028 -0.036  0.028  0.22 ]
     [ 0.412  0.22   0.156  0.22   0.412]]

    Raises
    ------
    ValueError
        If the parameters are the wrong type.
    ValueError
        If `num_cell_y` is not given for a 2D solution.
    RuntimeError
        If the SWASHES executable is not found
    RuntimeError
        When the SWASHES call returns an error
    """

    COLS = {'(i-0.5)*dx': X, '(j-0.5)*dy': Y, 'h[i][j]': DEPTH,
            'u[i][j]': VEL_X, 'v[i][j]': VEL_Y,
            'topo[i][j]+h[i][j]': HEAD, 'topo[i][j]': GD_ELEVATION,
            '||U||[i][j]': VEL2D, 'Fr[i][j]': FROUDE,
            'qx[i][j]': FLOW_X, 'qy[i][j]': FLOW_Y, 'q[i][j]': FLOW}

    def __init__(self, stype, domain, choice, num_cell_x, num_cell_y,
                 swashes_bin=''):
        SWASHES.__init__(self, 2., stype, domain, choice,
                         num_cell_x, num_cell_y, swashes_bin=swashes_bin)

    def dataframe(self):
        """Return a pandas DataFrame with two indices.

        Returns
        -------
        Pandas dataframe
            The X in meters is the index.

        Examples
        --------

        >>> import pyswashes
        >>> thacker = pyswashes.TwoDimensional(1, 1, 1, 3, 3)

        Get the ground elevation Pandas Series:

        >>> print(thacker.dataframe()[pyswashes.pyswashes.GD_ELEVATION])
        x         y       
        0.666667  0.666667    0.255556
                  2.000000    0.077778
                  3.333330    0.255556
        2.000000  0.666667    0.077778
                  2.000000   -0.100000
                  3.333330    0.077778
        3.333330  0.666667    0.255556
                  2.000000    0.077778
                  3.333330    0.255556
        Name: gd_elev, dtype: float64
        """
        csv = StringIO(self.csv())
        return pd.read_csv(csv, index_col=[0, 1])

    def np_array(self, value):
        """Return a NumPy ndarray of the given value.

        Returns
        -------
        NumPy ndarray

        Examples
        --------

        >>> import pyswashes
        >>> s = pyswashes.TwoDimensional(1,1,1,5,5)
        >>> print(s.np_array('depth'))
        [[ 0.     0.     0.     0.     0.   ]
         [ 0.     0.     0.025  0.     0.   ]
         [ 0.     0.025  0.125  0.025  0.   ]
         [ 0.     0.     0.025  0.     0.   ]
         [ 0.     0.     0.     0.     0.   ]]

        """
        # return the indices as columns
        df = self.dataframe().reset_index(drop=False)
        # pivot and get the values as a numpy ndarray
        return df.pivot(index=Y, columns=X, values=value).values

    def ascii_grid(self, value, filename):
        """Write an ascii grid GIS file.

        The lowest left corner is set to the coordinates 0,0.

        Parameters
        ----------
        value : str
            A value from `cols()`.
        filename : str
            Path to the file to write.

        Examples
        --------

        >>> import pyswashes
        >>> thacker = pyswashes.TwoDimensional(1, 1, 1, 3, 3)
        >>> thacker.ascii_grid('depth', 'thacker.asc')
        >>> with open('thacker.asc', 'r') as test_file:
        ...     for l in test_file:
        ...             print(l.strip())
        ... 
        NCOLS 3
        NROWS 3
        XLLCORNER 0.0
        YLLCORNER 0.0
        DX 1.33333
        DY 1.33333
        NODATA_VALUE -99999
        <BLANKLINE>
        0.000000 0.000000 0.000000
        0.000000 0.125000 0.000000
        0.000000 0.000000 0.000000
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
