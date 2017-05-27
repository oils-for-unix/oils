#!/usr/bin/python
"""
base.py -- Common base classes.
"""

class ParseError:
  """A parse error that can be formatted.

  Formatting is in ui.PrintError.
  """
  def __init__(self, msg, *args, **kwargs):
    self.msg = msg
    self.args = args
    # NOTE: We use a kwargs dict because Python 2 doesn't have keyword-only
    # args.
    self.token = kwargs.pop('token', None)
    self.word = kwargs.pop('word', None)
    if kwargs:
      raise AssertionError('Invalid keyword args %s' % kwargs)

  def UserErrorString(self):
    return self.msg % self.args
