"""Test the entry parameters of the SWASHES object
"""

from pyswashes import SWASHES


def test_get_df():
    s = SWASHES(1, 2, 1, 2, 10)
    s.get_dataframe()
