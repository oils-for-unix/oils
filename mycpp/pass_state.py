"""
pass_state.py
"""
from __future__ import print_function

import sys

from collections import defaultdict

#from mycpp.util import log


class Virtual(object):
  """
  See unit test for example usage.
  """

  def __init__(self) -> None:
    self.methods: dict[str, list[str]] = defaultdict(list)
    self.subclasses: dict[str, list[str]] = defaultdict(list)
    self.virtuals: list[tuple[str, str]] = []

  # These are called on the Forward Declare pass
  def OnMethod(self, class_name: str, method_name: str) -> None:
    #log('OnMethod %s %s', class_name, method_name)
    self.methods[class_name].append(method_name)

  def OnSubclass(self, base_class: str, subclass: str) -> None:
    # hack for vm::_Executor, etc.  This would fail if we have two base classes
    # in different namespaces with the same name.
    if '::' in base_class:
      base_class = base_class.split('::')[1]
    #log('OnSubclass %s', base_class, subclass)

    self.subclasses[base_class].append(subclass)
    # If this happens

  def Calculate(self) -> None:
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
  def IsVirtual(self, class_name: str, method_name: str) -> bool:
    return (class_name, method_name) in self.virtuals

