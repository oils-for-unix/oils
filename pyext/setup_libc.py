#!/usr/bin/env python2
from distutils.core import setup, Extension

module = Extension('libc',
                    sources = ['pyext/libc.c'],
                    # for #include "_build/detected-config.h"
                    extra_compile_args = ['-I', '.'],
                    undef_macros = ['NDEBUG'])

setup(name = 'libc',
      version = '1.0',
      description = 'Module for libc functions like fnmatch()',
      ext_modules = [module])
