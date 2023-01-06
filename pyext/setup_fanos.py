#!/usr/bin/env python2
from distutils.core import setup, Extension

module = Extension('fanos',
                    sources = ['cpp/fanos_shared.c', 'pyext/fanos.c'],
                    include_dirs = ['.'],
                    undef_macros = ['NDEBUG'])

setup(name = 'fanos',
      version = '1.0',
      description = 'FANOS: File descriptors and Netstrings Over Sockets',
      ext_modules = [module])
