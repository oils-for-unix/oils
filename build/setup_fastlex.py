#!/usr/bin/env python2
from distutils.core import setup, Extension

# https://stackoverflow.com/questions/4541565/how-can-i-assert-from-python-c-code
module = Extension('fastlex',
                    sources = ['native/fastlex.c'],
                    undef_macros = ['NDEBUG'],
                    # YYMARKER is sometimes unused; other times it's not
                    # Shut this up for build/dev.sh all.  We'll still see it in
                    # C++ inc ase we figure out how to fix it.
                    extra_compile_args = ['-Wno-unused-variable'],
                    )

setup(name = 'fastlex',
      version = '1.0',
      description = 'Module to speed up lexers',
      include_dirs = ['.'],
      ext_modules = [module])
