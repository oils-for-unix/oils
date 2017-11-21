#!/usr/bin/env python
from distutils.core import setup, Extension

module = Extension('libc',
                    sources = ['native/libc.c'])

setup(name = 'libc',
      version = '1.0',
      description = 'Module for libc functions like fnmatch()',
      ext_modules = [module])

module = Extension('lex',
                    sources = ['native/lex.c'])

setup(name = 'lex',
      version = '1.0',
      description = 'Module to speed up lexers',
      include_dirs = ['_build/gen'],
      ext_modules = [module])
