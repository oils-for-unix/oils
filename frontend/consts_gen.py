#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
consts_gen.py - Code generation for consts.py, id_kind_def.py, etc.
"""
from __future__ import print_function

import collections
import os
import sys

from asdl import gen_cpp
from mycpp.mylib import log
from frontend import id_kind_def
from frontend import builtin_def
from frontend import option_def


def _CreateModule(id_spec, ids):
    """Create a SYNTHETIC ASDL module to generate code from."""
    from asdl import ast

    id_variants = [ast.Constructor(name) for name, _ in ids]
    # Pack it in 16 bits
    id_sum = ast.SimpleSum(id_variants,
                           generate=['uint16', 'no_namespace_suffix'])

    kind_variants = [ast.Constructor(name) for name in id_spec.kind_name_list]
    kind_sum = ast.SimpleSum(kind_variants, generate=['no_namespace_suffix'])

    # Id = Word_Compound | Arith_Semi | Arith_Comma | ...
    id_ = ast.TypeDecl('Id', id_sum)
    kind_ = ast.TypeDecl('Kind', kind_sum)

    schema_ast = ast.Module('id_kind', [], [id_, kind_])
    return schema_ast


_BUILTINS = builtin_def.All()


def GenBuiltinLookup(func_name, kind, f):
    #log('%r %r', func_name, kind)

    pairs = [(b.name, b.index) for b in _BUILTINS if b.kind == kind]

    GenStringLookup('builtin_t', func_name, pairs, f)


def GenStringLookup(type_name, func_name, pairs, f):
    #log('%s', pairs)

    groups = collections.defaultdict(list)
    for name, index in pairs:
        first_char = name[0]
        groups[first_char].append((name, index))

    if 0:
        for first_char, pairs in groups.iteritems():
            log('%s %d', first_char, len(pairs))
            log('%s', pairs)

    # Note: we could optimize the length check, e.g. have a second level
    # switch.  But we would need to measure the difference.  Caching the id on
    # AST nodes is probably a bigger win, e.g. for loops.
    #
    # Size optimization: don't repeat constants literally?

    f.write("""\
%s %s(BigStr* s) {
  int length = len(s);
  if (length == 0) return 0;  // consts.NO_INDEX

  const char* data = s->data_;
  switch (data[0]) {
""" % (type_name, func_name))

    for first_char in sorted(groups):
        pairs = groups[first_char]
        f.write("  case '%s':\n" % first_char)
        for name, index in pairs:
            # NOTE: we have to check the length because they're not NUL-terminated
            f.write('''\
    if (length == %d && memcmp("%s", data, %d) == 0) return %d;
''' % (len(name), name, len(name), index))
        f.write('    break;\n')

    f.write("""\
  }

  return 0;  // consts.NO_INDEX
}

""")


def GenIntStrLookup(func_name, int2str, f):
    # NOTE: quoting doesn't work, strings must be Identifier Names here

    for i in sorted(int2str):
        s = int2str[i]
        f.write('GLOBAL_STR(k%s_%d, "%s");\n' % (func_name, i, s))

    f.write("""\

BigStr* %s(int i) {
  switch (i) {
""" % func_name)

    for i in sorted(int2str):
        s = int2str[i]
        f.write('  case %d:\n' % i)
        f.write('    return k%s_%d;\n' % (func_name, i))
        f.write('    break;\n')
    f.write("""\
  default:
    FAIL(kShouldNotGetHere);
  }
}

""")


def GenStringMembership(func_name, strs, f):
    groups = collections.defaultdict(list)
    for s in strs:
        first_char = s[0]
        groups[first_char].append(s)

    f.write("""\
bool %s(BigStr* s) {
  int length = len(s);
  if (length == 0) return false;

  const char* data = s->data_;
  switch (data[0]) {
""" % func_name)

    for first_char in sorted(groups):
        strs = groups[first_char]
        f.write("  case '%s':\n" % first_char)
        for s in strs:
            # NOTE: we have to check the length because they're not NUL-terminated
            f.write('''\
    if (length == %d && memcmp("%s", data, %d) == 0) return true;
''' % (len(s), s, len(s)))
        f.write('    break;\n')

    f.write("""\
  }

  return false;
}

""")


C_CHAR = {
    # '\'' is a single quote in C
    "'": "\\'",
    '"': '\\"',
    '\\': "\\\\",
    '\t': '\\t',
    '\r': '\\r',
    '\n': '\\n',
    '\v': '\\v',
    '\0': '\\0',
    '\a': '\\a',
    '\b': '\\b',
    '\f': '\\f',
    '\x1b': '\\x1b',
}


def CChar(c):
    return C_CHAR.get(c, c)


def GenCharLookup(func_name, lookup, f, required=False):
    f.write("""\
BigStr* %s(BigStr* c) {
  assert(len(c) == 1);

  char ch = c->data_[0];

  // TODO-intern: return value
  switch (ch) {
""" % func_name)

    for char_code in sorted(lookup):
        f.write("  case '%s':\n" % CChar(char_code))
        f.write('    return StrFromC("%s", 1);\n' % CChar(lookup[char_code]))
        f.write("    break;\n")

    f.write("  default:\n")
    if required:
        f.write("    assert(0);\n")
    else:
        f.write("    return nullptr;\n")

    f.write("""
  }
}
""")


def GenStrList(l, name, out):
    element_globals = []
    for i, elem in enumerate(l):
        global_name = "k%s_%d" % (name, i)
        out('GLOBAL_STR(%s, "%s");', global_name, elem)
        element_globals.append(global_name)

    lit = ' COMMA '.join(element_globals)
    out('GLOBAL_LIST(%s, BigStr*, %d, {%s});\n', name, len(l), lit)


def main(argv):
    try:
        action = argv[1]
    except IndexError:
        raise RuntimeError('Action required')

    # TODO: Remove duplication in core/meta.py
    ID_TO_KIND = {}
    BOOL_ARG_TYPES = {}
    TEST_UNARY_LOOKUP = {}
    TEST_BINARY_LOOKUP = {}
    TEST_OTHER_LOOKUP = {}

    ID_SPEC = id_kind_def.IdSpec(ID_TO_KIND, BOOL_ARG_TYPES)

    id_kind_def.AddKinds(ID_SPEC)
    id_kind_def.AddBoolKinds(ID_SPEC)  # must come second

    id_kind_def.SetupTestBuiltin(ID_SPEC, TEST_UNARY_LOOKUP,
                                 TEST_BINARY_LOOKUP, TEST_OTHER_LOOKUP)

    ids = ID_SPEC.id_str2int.items()
    ids.sort(key=lambda pair: pair[1])  # Sort by ID

    if action == 'c':
        for name, id_int in ids:
            print('#define id__%s %s' % (name, id_int))

    elif action == 'cpp':
        schema_ast = _CreateModule(ID_SPEC, ids)

        out_prefix = argv[2]

        with open(out_prefix + '.h', 'w') as f:
            f.write("""\
#ifndef ID_KIND_ASDL_H
#define ID_KIND_ASDL_H

#include <stdint.h>  // uint16_t

class BigStr;

namespace id_kind_asdl {

#define ASDL_NAMES struct
""")

            v = gen_cpp.ClassDefVisitor(f)
            v.VisitModule(schema_ast)

            f.write("""
}  // namespace id_kind_asdl

#endif  // ID_KIND_ASDL_H
""")

        with open(out_prefix + '.cc', 'w') as f:
            f.write("""\
#include <assert.h>
#include "_gen/frontend/id_kind.asdl.h"
#include "mycpp/gc_alloc.h"  // StrFromC()

namespace id_kind_asdl {

""")

            v = gen_cpp.MethodDefVisitor(f)

            v.VisitModule(schema_ast)

            f.write('}  // namespace id_kind_asdl\n')

    elif action == 'mypy':
        from asdl import gen_python

        schema_ast = _CreateModule(ID_SPEC, ids)
        #print(schema_ast)

        f = sys.stdout

        f.write("""\
from asdl import pybase

""")
        # Minor style issue: we want Id and Kind, not Id_e and Kind_e
        v = gen_python.GenMyPyVisitor(f)
        v.VisitModule(schema_ast)

    elif action == 'cpp-consts':

        # Break circular deps

        from core import pyutil
        from frontend import consts
        from _devbuild.gen.id_kind_asdl import Id_str, Kind_str
        from _devbuild.gen.types_asdl import redir_arg_type_str, bool_arg_type_str

        LIST_INT = [
            'STRICT_ALL',
            'YSH_UPGRADE',
            'YSH_ALL',
            'DEFAULT_TRUE',
            'PARSE_OPTION_NUMS',
            'SHOPT_OPTION_NUMS',
            'SET_OPTION_NUMS',
            'VISIBLE_SHOPT_NUMS',
        ]

        prefix = argv[2]

        with open(prefix + '.h', 'w') as f:

            def out(fmt, *args):
                print(fmt % args, file=f)

            out("""\
#ifndef CONSTS_H
#define CONSTS_H

#include "mycpp/runtime.h"

#include "_gen/frontend/id_kind.asdl.h"
#include "_gen/frontend/option.asdl.h"
#include "_gen/core/runtime.asdl.h"
#include "_gen/frontend/types.asdl.h"

namespace consts {
""")

            for name in LIST_INT:
                out('extern List<int>* %s;', name)

            out('extern List<BigStr*>* BUILTIN_NAMES;')
            out('extern List<BigStr*>* OSH_KEYWORD_NAMES;')
            out('extern List<BigStr*>* SET_OPTION_NAMES;')
            out('extern List<BigStr*>* SHOPT_OPTION_NAMES;')

            out("""\

extern int NO_INDEX;

extern BigStr* gVersion;

int RedirDefaultFd(id_kind_asdl::Id_t id);
types_asdl::redir_arg_type_t RedirArgType(id_kind_asdl::Id_t id);
types_asdl::bool_arg_type_t BoolArgType(id_kind_asdl::Id_t id);
id_kind_asdl::Kind GetKind(id_kind_asdl::Id_t id);

types_asdl::opt_group_t OptionGroupNum(BigStr* s);
option_asdl::option_t OptionNum(BigStr* s);
option_asdl::builtin_t LookupNormalBuiltin(BigStr* s);
option_asdl::builtin_t LookupAssignBuiltin(BigStr* s);
option_asdl::builtin_t LookupSpecialBuiltin(BigStr* s);
bool IsControlFlow(BigStr* s);
BigStr* ControlFlowName(int i);
bool IsKeyword(BigStr* s);
BigStr* LookupCharC(BigStr* c);
BigStr* LookupCharPrompt(BigStr* c);

BigStr* OptionName(option_asdl::option_t opt_num);

Tuple2<runtime_asdl::state_t, runtime_asdl::emit_t> IfsEdge(runtime_asdl::state_t state, runtime_asdl::char_kind_t ch);

extern BigStr* ASSIGN_ARG_RE;
extern BigStr* TEST_V_RE;
extern BigStr* ARITH_INT_HEX_RE;
extern BigStr* ARITH_INT_OCT_RE;
extern BigStr* ARITH_INT_DEC_RE;
extern BigStr* ARITH_INT_ARB_RE;

}  // namespace consts

#endif  // CONSTS_H
""")
        with open(prefix + '.cc', 'w') as f:

            def out(fmt, *args):
                print(fmt % args, file=f)

            out("""\
#include "_gen/frontend/consts.h"

using id_kind_asdl::Id;
using id_kind_asdl::Kind;
using types_asdl::redir_arg_type_e;
using types_asdl::bool_arg_type_e;
using option_asdl::builtin_t;

namespace consts {

int NO_INDEX = 0;  // duplicated from frontend/consts.py
""")

            # Generate gVersion, which is read by pyutil::GetVersion()
            this_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            root_dir = os.path.join(this_dir, '..')  # ~/git/oilshell/oil
            loader = pyutil._FileResourceLoader(root_dir)

            version_str = pyutil.GetVersion(loader)
            out('GLOBAL_STR(gVersion, "%s");' % version_str)
            out('')

            # Note: could use opt_num:: instead of raw ints
            for name in LIST_INT:
                val = getattr(consts, name)
                val_str = ' COMMA '.join(str(i) for i in val)
                out('GLOBAL_LIST(%s, int, %d, {%s});', name, len(val), val_str)

            out("""\

int RedirDefaultFd(id_kind_asdl::Id_t id) {
  // relies on "switch lowering"
  switch (id) {
""")
            for id_ in sorted(consts.REDIR_DEFAULT_FD):
                a = Id_str(id_).replace('.', '::')
                b = consts.REDIR_DEFAULT_FD[id_]
                out('  case %s: return %s;' % (a, b))
            out("""\
  }
  FAIL(kShouldNotGetHere);
}
""")

            out("""\
types_asdl::redir_arg_type_t RedirArgType(id_kind_asdl::Id_t id) {
  // relies on "switch lowering"
  switch (id) {
""")
            for id_ in sorted(consts.REDIR_ARG_TYPES):
                a = Id_str(id_).replace('.', '::')
                # redir_arg_type_e::Path, etc.
                b = redir_arg_type_str(consts.REDIR_ARG_TYPES[id_]).replace(
                    '.', '_e::')
                out('  case %s: return %s;' % (a, b))
            out("""\
  }
  FAIL(kShouldNotGetHere);
}
""")

            out("""\
types_asdl::bool_arg_type_t BoolArgType(id_kind_asdl::Id_t id) {
  // relies on "switch lowering"
  switch (id) {
""")
            for id_ in sorted(BOOL_ARG_TYPES):
                a = Id_str(id_).replace('.', '::')
                # bool_arg_type_e::BigStr, etc.
                b = bool_arg_type_str(BOOL_ARG_TYPES[id_]).replace('.', '_e::')
                out('  case %s: return %s;' % (a, b))
            out("""\
  }
  FAIL(kShouldNotGetHere);
}
""")

            out("""\
Kind GetKind(id_kind_asdl::Id_t id) {
  // relies on "switch lowering"
  switch (id) {
""")
            for id_ in sorted(ID_TO_KIND):
                a = Id_str(id_).replace('.', '::')
                b = Kind_str(ID_TO_KIND[id_]).replace('.', '::')
                out('  case %s: return %s;' % (a, b))
            out("""\
  }
  FAIL(kShouldNotGetHere);
}
""")

            pairs = consts.OPTION_GROUPS.items()
            GenStringLookup('types_asdl::opt_group_t', 'OptionGroupNum', pairs,
                            f)

            pairs = [(opt.name, opt.index) for opt in option_def.All()]
            GenStringLookup('option_asdl::option_t', 'OptionNum', pairs, f)

            GenBuiltinLookup('LookupNormalBuiltin', 'normal', f)
            GenBuiltinLookup('LookupAssignBuiltin', 'assign', f)
            GenBuiltinLookup('LookupSpecialBuiltin', 'special', f)

            GenStringMembership('IsControlFlow', consts._CONTROL_FLOW_NAMES, f)
            GenIntStrLookup('ControlFlowName', consts._CONTROL_FLOW_LOOKUP, f)

            GenStringMembership('IsKeyword', consts.OSH_KEYWORD_NAMES, f)

            GenCharLookup('LookupCharC', consts._ONE_CHAR_C, f, required=True)
            GenCharLookup('LookupCharPrompt', consts._ONE_CHAR_PROMPT, f)

            opt_int2str = {}
            for opt in option_def.All():
                opt_int2str[opt.index] = opt.name
            GenIntStrLookup('OptionName', opt_int2str, f)

            #
            # Generate a tightly packed 2D array for C, from a Python dict.
            #

            edges = consts._IFS_EDGES
            max_state = max(edge[0] for edge in edges)
            max_char_kind = max(edge[1] for edge in edges)

            edge_array = []
            for i in xrange(max_state + 1):
                # unused cells get -1
                edge_array.append(['-1'] * (max_char_kind + 1))

            for i in xrange(max_state + 1):
                for j in xrange(max_char_kind + 1):
                    entry = edges.get((i, j))
                    if entry is not None:
                        # pack (new_state, action) into 32 bits
                        edge_array[i][j] = '(%d<<16)|%d' % entry

            parts = []
            for i in xrange(max_state + 1):
                parts.append('  {')
                parts.append(', '.join('%10s' % cell
                                       for cell in edge_array[i]))
                parts.append(' },\n')

            out("""\
int _IFS_EDGE[%d][%d] = { 
%s
};
""" % (max_state + 1, max_char_kind + 1, ''.join(parts)))

            out("""\
// Note: all of these are integers, e.g. state_i, emit_i, char_kind_i
using runtime_asdl::state_t;
using runtime_asdl::emit_t;
using runtime_asdl::char_kind_t;

Tuple2<state_t, emit_t> IfsEdge(state_t state, runtime_asdl::char_kind_t ch) {
  int cell = _IFS_EDGE[state][ch];
  state_t new_state = cell >> 16;
  emit_t emit = cell & 0xFFFF;
  return Tuple2<state_t, emit_t>(new_state, emit);
}
""")

            GenStrList(consts.BUILTIN_NAMES, 'BUILTIN_NAMES', out)
            GenStrList(consts.OSH_KEYWORD_NAMES, 'OSH_KEYWORD_NAMES', out)
            GenStrList(consts.SET_OPTION_NAMES, 'SET_OPTION_NAMES', out)
            GenStrList(consts.SHOPT_OPTION_NAMES, 'SHOPT_OPTION_NAMES', out)

            def _CString(s):
                # Hack that does backslash escaping, e.g. \\
                # We could also use C++ strings
                import json
                return json.dumps(s)

            GLOBAL_STRINGS = [
                'ASSIGN_ARG_RE',
                'TEST_V_RE',
                'ARITH_INT_HEX_RE',
                'ARITH_INT_OCT_RE',
                'ARITH_INT_DEC_RE',
                'ARITH_INT_ARB_RE',
            ]
            for var_name in GLOBAL_STRINGS:
                out('GLOBAL_STR(%s, %s);', var_name,
                    _CString(getattr(consts, var_name)))

            out("""\
}  // namespace consts
""")

    elif action == 'py-consts':
        # It's kind of weird to use the generated code to generate more code.
        # Can we do this instead with the parsed module for "id" and "types.asdl"?

        from frontend import consts
        from _devbuild.gen.id_kind_asdl import Id_str, Kind_str
        from _devbuild.gen.types_asdl import redir_arg_type_str, bool_arg_type_str

        print("""
from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.types_asdl import redir_arg_type_e, bool_arg_type_e
""")

        print('')
        print('BOOL_ARG_TYPES = {')
        for id_ in sorted(BOOL_ARG_TYPES):
            v = BOOL_ARG_TYPES[id_]
            # HACK
            v = bool_arg_type_str(v).replace('.', '_e.')
            print('  %s: %s,' % (Id_str(id_), v))
        print('}')

        print('')
        print('TEST_UNARY_LOOKUP = {')
        for op_str in sorted(TEST_UNARY_LOOKUP):
            v = Id_str(TEST_UNARY_LOOKUP[op_str])
            print('  %r: %s,' % (op_str, v))
        print('}')

        print('')
        print('TEST_BINARY_LOOKUP = {')
        for op_str in sorted(TEST_BINARY_LOOKUP):
            v = Id_str(TEST_BINARY_LOOKUP[op_str])
            print('  %r: %s,' % (op_str, v))
        print('}')

        print('')
        print('TEST_OTHER_LOOKUP = {')
        for op_str in sorted(TEST_OTHER_LOOKUP):
            v = Id_str(TEST_OTHER_LOOKUP[op_str])
            print('  %r: %s,' % (op_str, v))
        print('}')

        print('')
        print('ID_TO_KIND = {')
        for id_ in sorted(ID_TO_KIND):
            v = Kind_str(ID_TO_KIND[id_])
            print('  %s: %s,' % (Id_str(id_), v))
        print('}')

    else:
        raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
    try:
        main(sys.argv)
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
