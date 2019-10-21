"""
pretty.py
"""

try:
  import fastlex
except ImportError:
  fastlex = None  # type: ignore

# Word characters, - and _, as well as path name characters . and /.
PLAIN_WORD_RE = r'[a-zA-Z0-9\-_./]+'

if fastlex:
  IsPlainWord = fastlex.IsPlainWord
else:
  import re

  _PLAIN_WORD_RE = re.compile(PLAIN_WORD_RE + '$')

  def IsPlainWord(s):
    # type: (str) -> bool
    if '\n' in s:  # account for the fact that $ matches the newline
      return False
    return bool(_PLAIN_WORD_RE.match(s))


# NOTE: bash prints \' for single quote, repr() prints "'".  Gah.  This is also
# used for printf %q and ${var@q} (bash 4.4).

def String(s):
  # type: (str) -> str
  """Return a human-friendly representation of an arbitrary shell string.

  Used for:

  - ASDL pretty printing
  - the 'xtrace' feature (core/devtools.py)
  - 'getopts' builtin error messages
  - Displaying argv in 'jobs'
  """
  if IsPlainWord(s):
    return s
  else:
    return repr(s)


# NOTE: Converting strings to JSON and can be a cheap hack for detecting
# invalid unicode.  But we want to write our own AST walker for that.

