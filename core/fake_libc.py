#!/usr/bin/python
"""
fake_libc.py

Pure Python stubs for libc.py.  They will cause some tests to fail.
"""


import fnmatch as fnmatch_mod
import glob as glob_mod
import re


def fnmatch(pat, s):
  return fnmatch_mod.fnmatch(pat, s)


def glob(pat):
  return glob_mod.glob(pat)


def regex_parse(regex):
  return True


def regex_match(regex, s):
  m = re.search(regex, s)
  return bool(m)
