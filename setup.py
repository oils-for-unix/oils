#!/usr/bin/env python2
"""
Build oil-dev as a Python application

This exists primarily to support nix-build, which supplies
all of the necessary dependencies.
"""
from setuptools import setup, find_packages, Extension

posix_ = Extension("posix_", sources=["native/posixmodule.c"])
line_input = Extension(
    "line_input",
    sources=["native/line_input.c"],
    undef_macros=["NDEBUG"],
    libraries=["readline"],
)
fastlex = Extension("fastlex", sources=["native/fastlex.c"], undef_macros=["NDEBUG"])
libc = Extension("libc", sources=["native/libc.c"], undef_macros=["NDEBUG"])

setup(
    name="oil",
    version="0.8",  # TODO: pull from elsewhere
    description="A new unix shell",
    packages=find_packages(),
    include_package_data=True,
    # For posix_methods.def
    include_dirs=["build/oil-defs", "_devbuild/gen"],  # posix_ & fastlex
    ext_modules=[posix_, line_input, fastlex, libc],
    scripts=["bin/oil.py", "bin/osh_eval.py", "bin/osh_parse.py"],
)
