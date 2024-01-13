#!/usr/bin/env python2
from distutils.core import setup, Extension

module = Extension('fastfunc',
                    sources = ['data_lang/j8_libc.c', 'pyext/fastfunc.c'],
                    include_dirs = ['.'],
                    undef_macros = ['NDEBUG'])

setup(name = 'fastfunc',
      version = '1.0',
      description = 'C functions like J8 encoding',
      ext_modules = [module])
