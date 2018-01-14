#!/usr/bin/env python

from distutils.core import setup, Extension
import numpy as np
import argparse, sys

argparser = argparse.ArgumentParser(add_help=False)
argparser.add_argument('--no-geo-pointinpolygon',
        dest='with_geo_pointinpolygon',
        help='optionally compile utils.geo.pointinpolygon extension',
        action='store_false')
args, unknown = argparser.parse_known_args()
sys.argv = [sys.argv[0]] + unknown
argparser.print_help()

_packages = ['phacsl',
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
