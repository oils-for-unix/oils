#!/usr/bin/env python2
from distutils.core import setup, Extension

module = Extension('libc',
                    sources = ['native/libc.c'],
                    undef_macros = ['NDEBUG'])

setup(name = 'libc',
      version = '1.0',
      description = 'Module for libc functions like fnmatch()',
      ext_modules = [module])
