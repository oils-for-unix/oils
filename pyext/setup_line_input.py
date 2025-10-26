#!/usr/bin/env python2
from distutils.core import setup, Extension
import sys
import os

# On macOS with Homebrew, explicitly point to readline location
extra_compile_args = []
extra_link_args = []
include_dirs = []
library_dirs = []

if sys.platform == 'darwin':
    # Try Homebrew locations (Apple Silicon and Intel)
    homebrew_prefixes = ['/opt/homebrew', '/usr/local']
    for prefix in homebrew_prefixes:
        readline_prefix = os.path.join(prefix, 'opt', 'readline')
        if os.path.exists(readline_prefix):
            include_dirs.append(os.path.join(readline_prefix, 'include'))
            library_dirs.append(os.path.join(readline_prefix, 'lib'))
            break

module = Extension('line_input',
                    sources = ['pyext/line_input.c'],
                    undef_macros = ['NDEBUG'],
                    libraries = ['readline'],
                    include_dirs = include_dirs,
                    library_dirs = library_dirs,
                    extra_compile_args = extra_compile_args,
                    extra_link_args = extra_link_args
                    )

setup(name = 'line_input',
      version = '1.0',
      description = 'Our readline/libedit binding',
      ext_modules = [module])
