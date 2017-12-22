#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
from setuptools import setup, find_packages


def get_long_description():
    with io.open('README.rst', 'r',  encoding='utf-8') as f:
        long_description = f.read()
    idx = max(0, long_description.find(u"pyswashes is"))
    return long_description[idx:]


CLASSIFIERS = ["Development Status :: 2 - Pre-Alpha",
               "Intended Audience :: Science/Research",
               "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
               "Operating System :: OS Independent",
               "Programming Language :: Python :: 3.6",
               "Topic :: Scientific/Engineering"]


DESCR = "a Python interface for SWASHES"


REQUIRES = ['pandas']


metadata = dict(name='pyswashes',
                version="0.1.0",
                description=DESCR,
                long_description=get_long_description(),
                author='Laurent Courty',
                author_email='laurent@courty.me',
                license='GPLv3',
                classifiers=CLASSIFIERS,
                keywords='science engineering hydraulics',
                install_requires=REQUIRES,
                include_package_data=True,
                packages=find_packages('src'),
                package_dir={'': 'src'}
                )


setup(**metadata)
