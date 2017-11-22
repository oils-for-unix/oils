#!/usr/bin/env python
from distutils.core import setup, Extension

module = Extension('libc',
                    sources = ['native/libc.c'],
                    undef_macros = ['NDEBUG'])

setup(name = 'libc',
      version = '1.0',
      description = 'Module for libc functions like fnmatch()',
      ext_modules = [module])

# https://stackoverflow.com/questions/4541565/how-can-i-assert-from-python-c-code
module = Extension('fastlex',
                    sources = ['native/fastlex.c'],
                    undef_macros = ['NDEBUG']
                    )

setup(name = 'fastlex',
      version = '1.0',
      description = 'Module to speed up lexers',
      include_dirs = ['_build/gen'],
      ext_modules = [module])
