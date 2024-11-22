#!/usr/bin/env python2
"""Option_gen.py."""
from __future__ import print_function

import sys

from asdl import ast
from frontend import builtin_def
from frontend import option_def


def _CreateSum(sum_name, variant_names):
    """Similar to frontend/id_kind_gen.py Usage of SYNTHETIC ASDL module:

    C++:

    using option_asdl::opt_num
    opt_num::nounset

    Python:
    from _devbuild.gen.option_asdl import opt_num
    opt_num.nounset
    """
    sum_ = ast.SimpleSum([ast.Constructor(name) for name in variant_names],
                         generate=['integers'])
    typ = ast.TypeDecl(sum_name, sum_)
    return typ


def main(argv):
    try:
        action = argv[1]
    except IndexError:
        raise RuntimeError('Action required')

    # generate builtin::echo, etc.
    # This relies on the assigned option numbers matching ASDL's numbering!
    # TODO: Allow controlling the integer values in ASDL enums?

    option = _CreateSum('option', [opt.name for opt in option_def.All()])
    builtin = _CreateSum('builtin', [b.enum_name for b in builtin_def.All()])
    # TODO: could shrink array later.
    # [opt.name for opt in option_def.All() if opt.implemented])

    schema_ast = ast.Module('option', [], [], [option, builtin])

    if action == 'cpp':
        from asdl import gen_cpp

        out_prefix = argv[2]

        with open(out_prefix + '.h', 'w') as f:
            f.write("""\
#ifndef OPTION_ASDL_H
#define OPTION_ASDL_H

namespace option_asdl {

#define ASDL_NAMES struct
""")

            # Don't need option_str()
            v = gen_cpp.ClassDefVisitor(f, pretty_print_methods=False)
            v.VisitModule(schema_ast)

            f.write("""
}  // namespace option_asdl

#endif  // OPTION_ASDL_H
""")

    elif action == 'mypy':
        from asdl import gen_python

        f = sys.stdout

        f.write("""\
from asdl import pybase

""")
        # option_i type
        v = gen_python.GenMyPyVisitor(f, None)
        v.VisitModule(schema_ast)

    else:
        raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
    try:
        main(sys.argv)
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
