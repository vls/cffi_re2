#!/usr/bin/env python
import os
try:
    import setuptools
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
from setuptools import setup, Extension
from setuptools import find_packages
import cffi_re2

mod_cre2 = Extension('_cre2', sources=['_cre2.cpp'], libraries=['re2'], include_dirs = ['/usr/local/include'])

setup(
    name='cffi_re2',
    license='MIT license',
    packages=find_packages(exclude=['tests*']),
    install_requires=['cffi>=0.7', 'six'],
    ext_modules=[mod_cre2],
    zip_safe=False,
    test_suite='nose.collector',
    tests_require=['nose'],
    setup_requires=['nose>=1.0'],
    version=cffi_re2.__version__,
    long_description=open("README.md").read(),
    description='Access re2 library using cffi',
    url="https://github.com/vls/cffi_re2"
)
