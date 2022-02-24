#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='txt2bin',
    packages=find_packages(),

    entry_points={
        'console_scripts': ['txt2bin=txt2bin:main']
    },
)
