"""Test the entry parameters of the SWASHES object
"""

import pyswashes


def test_swashes_dataframe():
    s = pyswashes.SWASHES(1, 2, 1, 2, 10)
    s.dataframe()


def test_1d_dataframe():
    s = pyswashes.OneDimensional(1, 1, 2, 10)
    s.dataframe()


def test_15d_dataframe():
    s = pyswashes.PseudoTwoDimensional(1, 1, 1, 10)
    s.dataframe()


def test_2d_dataframe():
    s = pyswashes.TwoDimensional(1, 1, 1, 10, 10)
    s.dataframe()
