"""
pass_state.py
"""
from __future__ import print_function

from collections import defaultdict
from typing import Optional

from mycpp.util import log

_ = log


class Virtual(object):
    """
  See unit test for example usage.
  """

    def __init__(self) -> None:
        self.methods: dict[str, list[str]] = defaultdict(list)
        self.subclasses: dict[str, list[str]] = defaultdict(list)
        self.virtuals: dict[tuple[str, str], Optional[tuple[str, str]]] = {}
        self.has_vtable: dict[str, bool] = {}
        self.can_reorder_fields: dict[str, bool] = {}

        # _Executor -> vm::_Executor
        self.base_class_unique: dict[str, str] = {}

    # These are called on the Forward Declare pass
    def OnMethod(self, class_name: str, method_name: str) -> None:
        #log('OnMethod %s %s', class_name, method_name)

        # __init__ and so forth don't count
        if method_name.startswith('__') and method_name.endswith('__'):
            return

        self.methods[class_name].append(method_name)

    def OnSubclass(self, base_class: str, subclass: str) -> None:
        if '::' in base_class:
            # Hack for
            #
            # class _Executor: pass
            #   versus
            # class MyExecutor(vm._Executor): pass
            base_key = base_class.split('::')[-1]

            # Fail if we have two base classes in different namespaces with the same
            # name.
            if base_key in self.base_class_unique:
                # Make sure we don't have collisions
                assert self.base_class_unique[base_key] == base_class or base_class in self.subclasses[self.base_class_unique[base_key]]
            else:
                self.base_class_unique[base_key] = base_class

        else:
            base_key = base_class

        self.subclasses[base_class].append(subclass)

    def Calculate(self) -> None:
        """
    Call this after the forward declare pass.

    TODO: Are there bugs based on conflicting class names?
    """
        for base_class, subclasses in self.subclasses.items():
            self.can_reorder_fields[base_class] = False

            for subclass in subclasses:
                self.can_reorder_fields[subclass] = False

                b_methods = self.methods[base_class]
                s_methods = self.methods[subclass]
                overlapping = set(b_methods) & set(s_methods)
                for method in overlapping:
                    self.virtuals[(base_class, method)] = None
                    self.virtuals[(subclass, method)] = (base_class, method)
                if overlapping:
                    self.has_vtable[base_class] = True
                    self.has_vtable[subclass] = True

    # These is called on the Decl pass
    def IsVirtual(self, class_name: str, method_name: str) -> bool:
        return (class_name, method_name) in self.virtuals

    def HasVTable(self, class_name: str) -> bool:
        return class_name in self.has_vtable

    def CanReorderFields(self, class_name: str) -> bool:
        if class_name in self.can_reorder_fields:
            return self.can_reorder_fields[class_name]
        else:
            return True  # by default they can be reordered
