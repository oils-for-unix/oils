#!/usr/bin/env python
from distutils.core import setup, Extension

module = Extension('libc',
                    sources = ['native/libc.c'])

setup(name = 'libc',
      version = '1.0',
      description = 'Module for libc functions like fnmatch()',
      ext_modules = [module])

module = Extension('fastlex',
                    sources = ['native/fastlex.c'])

setup(name = 'fastlex',
      version = '1.0',
      description = 'Module to speed up lexers',
      include_dirs = ['_build/gen'],
      ext_modules = [module])
