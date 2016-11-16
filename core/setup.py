#!/usr/bin/env python3

from distutils.core import setup, Extension

module = Extension('libc',
                    sources = ['libc.c'])

setup(name = 'libc',
      version = '1.0',
      description = 'Module for libc functions like fnmatch()',
      ext_modules = [module])
