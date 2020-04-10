"""
pretty.py

TODO: Fold in IsPlainWord into core/qsn.py.
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
