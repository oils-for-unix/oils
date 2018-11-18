#!/usr/bin/python
"""
oil_exec.py
"""

class OilExecutor(object):
  def __init__(self, osh_ex):
    self.osh_ex = osh_ex
    # TODO: This is separate from OSH?  But does it share globals?  Should we
    # allow 'source'?  The syntax in Oil could be GLOBALS.foo ?
    self.mem = None

  def MaybeRunExitTrap(self):
    # TODO: Delegate to osh_ex?
    # Do we have a trap builtin?
    return None
