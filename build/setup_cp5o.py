#!/usr/bin/env python2
from distutils.core import setup, Extension

module = Extension('cp5o',
                    sources = ['native/cp5o.c'],
                    undef_macros = ['NDEBUG'])

setup(name = 'cp5o',
      version = '1.0',
      description = 'cp5o: The Coprocess Protocol',
      ext_modules = [module])
