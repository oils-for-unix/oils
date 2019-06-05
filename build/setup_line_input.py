#!/usr/bin/env python2
from distutils.core import setup, Extension

module = Extension('line_input',
                    sources = ['native/line_input.c'],
                    undef_macros = ['NDEBUG'],
                    libraries = ['readline']
                    )

setup(name = 'line_input',
      version = '1.0',
      description = 'Our readline/libedit binding',
      ext_modules = [module])
