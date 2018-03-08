#!/usr/bin/env python

try:
    from setuptools import setup, Extension
except:
    from distutils.core import setup, Extension
import numpy as np
import argparse, sys

argparser = argparse.ArgumentParser(add_help=False)

argparser.add_argument('--no-geo-pointinpolygon',
        dest='with_geo_pointinpolygon',
        help='optionally compile utils.geo.pointinpolygon extension',
        action='store_false')

argparser.add_argument('--no-bitset',
        dest='with_bitset',
        help='optionally compile utils.collections.cbits extension',
        action='store_false')

args, unknown = argparser.parse_known_args()
sys.argv = [sys.argv[0]] + unknown
argparser.print_help()

_packages = [
        'phacsl',
        'phacsl.utils', 
        'phacsl.utils.misc',
        'phacsl.utils.collections',
        'phacsl.utils.formats',
        'phacsl.utils.geo',
        'phacsl.utils.notes',
        'phacsl.utils.tests',
        'phacsl.utils.classutils',
        'phacsl.stats', 
    ]

_ext_modules = []

if args.with_geo_pointinpolygon:
    _packages.append('phacsl.utils.geo.pointinpolygon')
    _ext_modules.append(Extension('phacsl.utils.geo.pointinpolygon.cext',
                sources= ['src/phacsl/utils/geo/pointinpolygon/c_ext/pointinpolygon.cpp']))

def make_cython_ext(modname, pyxfilename):
    import numpy
    import os
    import sys
    from Cython.Build import cythonize
    if sys.platform == 'darwin':
        os.environ['CC'] = 'gcc-7'
        os.environ['CXX'] = 'g++-7'
    else:
        os.environ['CC'] = 'gcc'
        os.environ['CXX'] = 'g++'
    from distutils.extension import Extension
    return cythonize([
        Extension(name=modname, sources=[pyxfilename],
            extra_compile_args=['-O3', '-march=native', '-fopenmp'],
            extra_link_args=['-fopenmp'],
            include_dirs=[
                numpy.get_include(),
                #'/usr/local/include/boost'
                ],
            #library_dirs=['/usr/local/lib'], 
            language="c++")], force=True)

if args.with_bitset:
    _ext_modules.extend(
        make_cython_ext('phacsl.utils.collections.cbits', 'src/phacsl/utils/collections/cbits.pyx'))

setup(name='phacsl-utils',
      version='0.0.1',
      description='Generic utilities shared by PHA software',
      author='PSC Public Health Applications',
      author_email='pha@psc.edu',
      #url='https://www.python.org/sigs/distutils-sig/',
      include_dirs = [np.get_include()], #add include path of numpy
      ext_modules = _ext_modules,
      packages = _packages,
      package_dir = {'': 'src'}
     )
