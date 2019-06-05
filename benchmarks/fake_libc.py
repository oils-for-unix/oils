"""
fake_libc.py

For PyPy.
"""

def regex_parse(regex_str):
  return True

# This makes things fall through to the first case statement...
def fnmatch(s, to_match):
  return True

