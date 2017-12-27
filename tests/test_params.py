"""Test the entry parameters of the SWASHES object
"""
import pytest
import subprocess

import pyswashes


def test_bin_is_wrong():
    with pytest.raises(RuntimeError, message="Expecting RuntimeError"):
        pyswashes.SWASHES(1, 2, 1, 2, 10, swashes_bin='this_is_not_swashes')


def test_xdim_is_wrong():
    with pytest.raises(RuntimeError, message="Expecting RuntimeError"):
        pyswashes.SWASHES(1, 2, 1, 2, 0)


def test_noydim():
    with pytest.raises(ValueError, message="Expecting ValueError"):
        pyswashes.SWASHES(2, 1, 1, 1, 10)


def test_wrong_type():
    with pytest.raises(ValueError, message="Expecting ValueError"):
        pyswashes.SWASHES(1,"b", 1, 1, 1, 10)


def test_invalid_dim():
    with pytest.raises(ValueError, message="Expecting ValueError"):
        pyswashes.SWASHES(1.2, 1, 1, 1, 1, 10)
