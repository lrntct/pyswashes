"""Test the classes and their methods
"""

import pytest
import numpy as np
import pandas as pd

import pyswashes


def test_swashes_dataframe():
    s = pyswashes.SWASHES(1, 2, 1, 2, 10)
    df = s.dataframe()
    assert isinstance(df, pd.DataFrame)


def test_1d_dataframe():
    s = pyswashes.OneDimensional(1, 1, 2, 10)
    df = s.dataframe()
    assert isinstance(df, pd.DataFrame)


def test_15d_dataframe():
    s = pyswashes.PseudoTwoDimensional(1, 1, 1, 10)
    df = s.dataframe()
    assert isinstance(df, pd.DataFrame)


def test_2d_dataframe():
    s = pyswashes.TwoDimensional(1, 1, 1, 10, 10)
    df = s.dataframe()
    assert isinstance(df, pd.DataFrame)

def test_1d_nparray_wrong_value():
    s = pyswashes.OneDimensional(1, 1, 2, 10)
    with pytest.raises(ValueError):
        arr = s.np_array(value='not_the_right_str')

def test_1d_topo():
    s = pyswashes.OneDimensional(1, 1, 2, 10)
    arr = s.np_topo()
    assert isinstance(arr, np.ndarray)
    assert arr.ndim == 1


def test_15d_topo():
    s = pyswashes.PseudoTwoDimensional(1, 1, 1, 10)
    arr = s.np_topo()
    assert isinstance(arr, np.ndarray)


def test_2d_topo():
    s = pyswashes.TwoDimensional(1, 1, 1, 10, 10)
    arr = s.np_topo()
    assert isinstance(arr, np.ndarray)
    assert arr.ndim == 2


def test_1d_depth():
    s = pyswashes.OneDimensional(1, 1, 2, 10)
    arr = s.np_depth()
    assert isinstance(arr, np.ndarray)
    assert arr.ndim == 1


def test_15d_depth():
    s = pyswashes.PseudoTwoDimensional(1, 1, 1, 10)
    arr = s.np_depth()
    assert isinstance(arr, np.ndarray)


def test_2d_depth():
    s = pyswashes.TwoDimensional(1, 1, 1, 10, 10)
    arr = s.np_depth()
    assert isinstance(arr, np.ndarray)
    assert arr.ndim == 2


def test_1d_ascii():
    s = pyswashes.OneDimensional(1, 1, 2, 10)
    s.ascii_grid('gd_elev', 'dem_test.asc')


def test_2d_ascii():
    s = pyswashes.TwoDimensional(1, 1, 1, 10, 10)
    s.ascii_grid('gd_elev', 'dem_test.asc')
