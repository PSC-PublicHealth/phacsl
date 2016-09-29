#!/usr/bin/env python

from distutils.core import setup, Extension
import numpy as np

ext_modules = [ Extension('phacsl.utils.geo.pointinpolygon.cext', sources= ['src/phacsl/utils/geo/pointinpolygon/c_ext/pointinpolygon.cpp']) ]

setup(name='phacsl-utils',
      version='0.0.1',
      description='Generic utilities shared by PHA software',
      author='Joel Welling',
      author_email='welling@psc.edu',
      #url='https://www.python.org/sigs/distutils-sig/',
      include_dirs = [np.get_include()], #add include path of numpy
      ext_modules = ext_modules,
      packages=['phacsl',
                'phacsl.utils', 
                'phacsl.utils.misc',
                'phacsl.utils.collections',
                'phacsl.utils.formats',
                'phacsl.utils.geo',
                'phacsl.utils.geo.pointinpolygon',
                'phacsl.utils.notes',
                'phacsl.utils.tests'
                ],
      package_dir = {'': 'src'}
     )
