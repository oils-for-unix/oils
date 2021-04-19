#!/usr/bin/env python2
from distutils.core import setup, Extension

module = Extension('nuds',
                    sources = ['native/nuds.c'],
                    undef_macros = ['NDEBUG'])

setup(name = 'nuds',
      version = '1.0',
      description = 'NUDS: Netstrings (and file descriptors) over Unix Domain Sockets',
      ext_modules = [module])
