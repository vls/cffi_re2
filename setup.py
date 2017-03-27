#!/usr/bin/env python
import os
import sys
try:
    import setuptools
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
from setuptools import setup, Extension
from setuptools import find_packages

mod_cre2 = Extension('cffi_re2._cre2', sources=['cre2.cpp'], libraries=['re2'],
    include_dirs=['/usr/local/include'], extra_compile_args=["-g", "-std=c++11"],
    extra_link_args=["-g"])

tests_require=['nose']
if sys.version_info < (2, 7):
    tests_require.append('nose_extra_tools')

setup(
    name='cffi_re2',
    license='MIT license',
    packages=find_packages(exclude=['tests*']),
    install_requires=['cffi>=0.7', 'six'],
    ext_modules=[mod_cre2],
    zip_safe=False,
    test_suite='nose.collector',
    tests_require=tests_require,
    setup_requires=['nose>=1.0'],
    version='0.2.1',
    long_description=open("README.md").read(),
    description='Access re2 library using cffi',
    url="https://github.com/vls/cffi_re2",
)
