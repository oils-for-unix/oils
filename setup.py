#!/usr/bin/python
from distutils.core import setup, Extension

module = Extension('libc',
                    sources = ['core/libc.c'])

setup(name = 'libc',
      version = '1.0',
      description = 'Module for libc functions like fnmatch()',
      ext_modules = [module])
