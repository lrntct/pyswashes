"""Test the entry parameters of the SWASHES object
"""
import pytest
import subprocess

from pyswashes import SWASHES


def test_bin_is_wrong():
    with pytest.raises(RuntimeError, message="Expecting RuntimeError"):
        SWASHES(1, 2, 1, 2, 10, swashes_bin='')


def test_xdim_is_wrong():
    with pytest.raises(RuntimeError, message="Expecting RuntimeError"):
        SWASHES(1, 2, 1, 2, 0)


def test_noydim():
    with pytest.raises(ValueError, message="Expecting ValueError"):
        SWASHES(2, 1, 1, 1, 10)


def test_wrong_type():
    with pytest.raises(ValueError, message="Expecting ValueError"):
        SWASHES(1,"b", 1, 1, 1, 10)


def test_invalid_dim():
    with pytest.raises(ValueError, message="Expecting ValueError"):
        SWASHES(1.2, 1, 1, 1, 1, 10)
