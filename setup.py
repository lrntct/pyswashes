#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
from setuptools import setup, find_packages


# see setup.cfg
metadata = dict(packages=find_packages('src'),
                package_dir={'': 'src'}
                )


setup(**metadata)
