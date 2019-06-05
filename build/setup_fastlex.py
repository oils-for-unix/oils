#!/usr/bin/env python2
from distutils.core import setup, Extension

# https://stackoverflow.com/questions/4541565/how-can-i-assert-from-python-c-code
module = Extension('fastlex',
                    sources = ['native/fastlex.c'],
                    undef_macros = ['NDEBUG']
                    )

setup(name = 'fastlex',
      version = '1.0',
      description = 'Module to speed up lexers',
      include_dirs = ['_devbuild/gen'],
      ext_modules = [module])
