Welcome to pyswashes
====================

|PyPI| |RTFD| |CircleCI| |codecov|

pyswashes is a python library that generates analytic solutions to the Shallow Water Equations.

With it to can obtain the selected analytic solution in the form of a csv, Pandas dataframe, NumPy array or ASCII Grid format.

The code is hosted on `GitHub <https://github.com/lrntct/pyswashes>`_.



Installation
============

pyswashes is available on the `Python package index <https://pypi.python.org/pypi/pyswashes>`_
and `anaconda <https://anaconda.org/lrntct/pyswashes>`_.

Installation with conda
-----------------------

It is recommended to install it through `conda`,
because it relies on the `swashes` package that cannot be installed with `pip`.

    conda install -c lrntct pyswashes


Installation with ppi
---------------------

    pip install pyswashes


Acknowledgements
================

pyswashes is an interface to the `SWASHES <https://sourcesup.renater.fr/projects/swashes/>`_ command line tool,
created by the University of Orléans, France.

SWASHES is detailed in the following article:

   SWASHES: a compilation of Shallow Water Analytic Solutions for Hydraulic and Environmental Studies',
   O. Delestre, C. Lucas, P.-A. Ksinant, F. Darboux, C. Laguerre, T.N.T. Vo, F. James, S. Cordier
   International Journal of Numerical Methods in Fluids, 2013, 72(3): 269-300.
   DOI: 10.1002/fld.3741 . URL: http://hal.archives-ouvertes.fr/hal-00628246


Indices and tables
==================

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   api


* :ref:`genindex`
.. ~ * :ref:`modindex`
* :ref:`search`


.. |CircleCI| image:: https://circleci.com/gh/lrntct/pyswashes.svg?style=svg
   :target: https://circleci.com/gh/lrntct/pyswashes
   :alt: CircleCI status
.. |codecov| image:: https://codecov.io/gh/lrntct/pyswashes/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/lrntct/pyswashes
   :alt: code coverage
.. |PyPI| image:: https://badge.fury.io/py/pyswashes.svg
   :target: https://badge.fury.io/py/pyswashes
   :alt: PyPI version
.. |RTFD| image:: https://readthedocs.org/projects/pyswashes/badge/?version=latest
   :target: http://pyswashes.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status
