#!/usr/bin/env python2
"""
symbols_test.py: Tests for symbols.py

Copied out of symbols.py.  You pass this some filenames.
"""

import sys
import symtable

from . import symbols
from . import transformer


def list_eq(l1, l2):
    return sorted(l1) == sorted(l2)

def get_names(syms):
    return [s for s in [s.get_name() for s in syms.get_symbols()]
            if not (s.startswith('_[') or s.startswith('.'))]


if __name__ == "__main__":
    # TODO: Pass symbols
    transformer.Init(None)

    for file in sys.argv[1:]:
        print(file)
        f = open(file)
        buf = f.read()
        f.close()
        syms = symtable.symtable(buf, file, "exec")
        mod_names = get_names(syms)

        #tree = parseFile(file)
        tree = None
        s = symbols.SymbolVisitor()
        s.Dispatch(tree)

        # compare module-level symbols
        names2 = s.scopes[tree].get_names()

        if not list_eq(mod_names, names2):
            print()
            print("oops", file)
            print(sorted(mod_names))
            print(sorted(names2))
            sys.exit(-1)

        d = {}
        d.update(s.scopes)
        del d[tree]
        scopes = d.values()
        del d

        for s in syms.get_symbols():
            if s.is_namespace():
                l = [sc for sc in scopes
                     if sc.name == s.get_name()]
                if len(l) > 1:
                    print("skipping", s.get_name())
                else:
                    if not list_eq(get_names(s.get_namespace()),
                                   l[0].get_names()):
                        print(s.get_name())
                        print(sorted(get_names(s.get_namespace())))
                        print(sorted(l[0].get_names()))
                        sys.exit(-1)
