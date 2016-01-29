#!/usr/bin/env python

from distutils.core import setup

setup(name='phacsl-utils',
      version='0.0.1',
      description='Generic utilities shared by PHA software',
      author='Joel Welling',
      author_email='welling@psc.edu',
      #url='https://www.python.org/sigs/distutils-sig/',
      packages=['phacsl.utils', 
                'phacsl.utils.misc',
                'phacsl.utils.collections',
                'phacsl.utils.formats',
                'phacsl.utils.notes',
                'phacsl.utils.tests'
                ],
      package_dir = {'': 'src'}
     )
