#!/usr/bin/env python3

from distutils.core import setup, Extension

module = Extension('libc3',
                    sources = ['core/libc3.c'])

setup(name = 'libc3',
      version = '1.0',
      description = 'Python 3 module for libc functions like fnmatch()',
      ext_modules = [module])
