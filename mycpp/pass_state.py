"""
pass_state.py
"""
from __future__ import print_function

import sys

from collections import defaultdict


class Virtual(object):
  """
  See unit test for example usage.
  """

  def __init__(self):
    self.methods = defaultdict(list)
    self.subclasses = defaultdict(list)
    self.virtuals = []  # type: List[Tuple[str, str]]

  # These are called on the Forward Declare pass
  def OnMethod(self, class_name, method_name):
    self.methods[class_name].append(method_name)

  def OnSubclass(self, base_class, subclass):
    self.subclasses[base_class].append(subclass)
    # If this happens

  def Calculate(self):
    """
    Call this after the forward declare pass.
    """
    for base_class, subclasses in self.subclasses.items():
      for subclass in subclasses:
        b_methods = self.methods[base_class]
        s_methods = self.methods[subclass]
        overlapping = set(b_methods) & set(s_methods)
        for method in overlapping:
          self.virtuals.append((base_class, method))
          self.virtuals.append((subclass, method))

  # These is called on the Decl pass
  def IsVirtual(self, class_name, method_name):
    return (class_name, method_name) in self.virtuals

