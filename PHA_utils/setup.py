#!/usr/bin/env python

from distutils.core import setup

setup(name='PHA_utils',
      version='0.0.1',
      description='Generic utilities shared by PHA software',
      author='Joel Welling',
      author_email='welling@psc.edu',
      #url='https://www.python.org/sigs/distutils-sig/',
      packages=['PHA_utils', 
                'PHA_utils.misc',
                'PHA_utils.formats',
                'PHA_utils.notes',
                'tests'
                ],
      package_dir = {'': 'src'}
     )