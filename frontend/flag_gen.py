#!/usr/bin/env python2
"""Flag_gen.py."""
from __future__ import print_function

import itertools
import sys

from _devbuild.gen.runtime_asdl import flag_type_e
from _devbuild.gen.value_asdl import value_e
from mycpp.mylib import log
from frontend import args
from frontend import flag_def  # side effect: flags are defined!
from frontend import flag_spec
from mycpp import mops
from mycpp.mylib import switch
# This causes a circular build dependency!  That is annoying.
# builtin_comp -> core/completion -> pylib/{os_path,path_stat,...} -> posix_
#from osh import builtin_comp

_ = flag_def


def CString(s):
    # HACKS for now

    assert '"' not in s, s
    assert '\\' not in s, s

    # For the default of write --end
    if s == '\n':
        return '"\\n"'

    return '"%s"' % s


def _WriteStrArray(f, var_name, a):
    c_strs = ', '.join(CString(s) for s in sorted(a))
    f.write('const char* %s[] = {%s, nullptr};\n' % (var_name, c_strs))
    f.write('\n')


def _WriteActionParams(f, actions, counter):
    param_names = []
    for key in sorted(actions):
        action = actions[key]
        to_write = None

        if isinstance(action, args.SetToString):
            if action.valid:
                to_write = action.valid

        elif isinstance(action, args.SetNamedOption):
            if action.names:
                to_write = action.names

        elif isinstance(action, args.SetNamedAction):
            if action.names:
                to_write = action.names

        if to_write:
            uniq = counter.next()
            var_name = 'params_%d' % uniq

            _WriteStrArray(f, var_name, to_write)
        else:
            var_name = None

        param_names.append(var_name)

    return param_names


def _WriteActions(f, var_name, actions, counter):
    # TODO: 'osh' and 'set' duplicate shopt params!!!  Maybe we want the entire
    # action not to be duplicated?
    param_names = _WriteActionParams(f, actions, counter)

    f.write('Action_c %s[] = {\n' % var_name)
    for i, key in enumerate(sorted(actions)):
        action = actions[key]
        #log('%s %s', key, action)

        name = None
        if isinstance(action, args.SetToString):
            if action.quit_parsing_flags:
                action_type = 'SetToString_q'
            else:
                action_type = 'SetToString'
            name = action.name

        elif isinstance(action, args.SetToInt):
            action_type = 'SetToInt'
            name = action.name

        elif isinstance(action, args.SetToFloat):
            action_type = 'SetToFloat'
            name = action.name

        elif isinstance(action, args.SetToTrue):
            action_type = 'SetToTrue'
            name = action.name

        elif isinstance(action, args.SetAttachedBool):
            action_type = 'SetAttachedBool'
            name = action.name

        elif isinstance(action, args.SetOption):
            action_type = 'SetOption'
            name = action.name

        elif isinstance(action, args.SetNamedOption):
            if action.shopt:
                action_type = 'SetNamedOption_shopt'
            else:
                action_type = 'SetNamedOption'

        elif isinstance(action, args.SetAction):
            action_type = 'SetAction'
            name = action.name

        elif isinstance(action, args.SetNamedAction):
            action_type = 'SetNamedAction'

        else:
            raise AssertionError(action)

        name_str = ('"%s"' % name) if name else 'nullptr'
        params_str = param_names[i] or 'nullptr'
        f.write('    {"%s", ActionType_c::%s, %s, %s},\n' %
                (key, action_type, name_str, params_str))
    #cc_f.write('SetToArg_c %s[] = {\n' % arity1_name)
    f.write('''\
    {},
};

''')


def _WriteDefaults(cc_f, defaults_name, defaults):
    cc_f.write('DefaultPair_c %s[] = {\n' % defaults_name)

    for name in sorted(defaults):
        val = defaults[name]
        if val.tag() == value_e.Bool:
            typ = 'Bool'
            v = '{.b = %s}' % ('true' if val.b else 'false')
        elif val.tag() == value_e.Int:
            typ = 'Int'
            v = '{.i = %s}' % mops.BigTruncate(val.i)
        elif val.tag() == value_e.Float:
            typ = 'Float'
            # printing this to C++ is problematic
            if val.f != -1.0:
                raise AssertionError('Float default not supported %r' % val.f)
            v = '{.f = -1.0}'
        elif val.tag() == value_e.Undef:
            typ = 'Str'  # default for string
            v = '{}'
        elif val.tag() == value_e.Str:
            # NOTE: 'osh' FlagSpecAndMore_ has default='nice' and default='abbrev-text'
            typ = 'Str'
            v = '{.s = %s}' % CString(val.s)

        else:
            raise AssertionError(val)

        cc_f.write('    {%s, flag_type_e::%s, %s},\n' %
                   (CString(name), typ, v))

    cc_f.write('''\
    {},
};

''')


def Cpp(specs, header_f, cc_f):
    counter = itertools.count()

    header_f.write("""\
// arg_types.h is generated by frontend/flag_gen.py

#ifndef ARG_TYPES_H
#define ARG_TYPES_H

#include "cpp/frontend_flag_spec.h"  // for FlagSpec_c
#include "mycpp/gc_mylib.h"

using value_asdl::value;
using value_asdl::value_e;

namespace arg_types {
""")
    for spec_name in sorted(specs):
        spec = specs[spec_name]

        if not spec.fields:
            continue  # skip empty 'eval' spec

        #
        # Figure out how to initialize the class
        #

        init_vals = []
        field_names = []
        field_decls = []
        bits = []
        for field_name in sorted(spec.fields):
            typ = spec.fields[field_name]
            field_name = field_name.replace('-', '_')
            field_names.append(field_name)

            with switch(typ) as case:
                if case(flag_type_e.Bool):
                    init_vals.append(
                        'static_cast<value::Bool*>(attrs->at(StrFromC("%s")))->b'
                        % field_name)
                    field_decls.append('bool %s;' % field_name)

                    # Bug that test should find
                    #bits.append('maskbit(offsetof(%s, %s))' % (spec_name, field_name))

                elif case(flag_type_e.Str):
                    # TODO: This code is ugly and inefficient!  Generate something
                    # better.  At least get rid of 'new' everywhere?
                    init_vals.append('''\
attrs->at(StrFromC("%s"))->tag() == value_e::Undef
          ? nullptr
          : static_cast<value::Str*>(attrs->at(StrFromC("%s")))->s''' %
                                     (field_name, field_name))

                    field_decls.append('BigStr* %s;' % field_name)

                    # BigStr* is a pointer type, so add a field here
                    bits.append('maskbit(offsetof(%s, %s))' %
                                (spec_name, field_name))

                elif case(flag_type_e.Int):
                    init_vals.append('''\
attrs->at(StrFromC("%s"))->tag() == value_e::Undef
          ? -1
          : static_cast<value::Int*>(attrs->at(StrFromC("%s")))->i''' %
                                     (field_name, field_name))
                    field_decls.append('int %s;' % field_name)

                elif case(flag_type_e.Float):
                    init_vals.append('''\
attrs->at(StrFromC("%s"))->tag() == value_e::Undef
          ? -1
          : static_cast<value::Float*>(attrs->at(StrFromC("%s")))->f''' %
                                     (field_name, field_name))
                    field_decls.append('float %s;' % field_name)

                else:
                    raise AssertionError(typ)

        #
        # Now emit the class
        #

        if bits:
            obj_tag = 'HeapTag::FixedSize'
            mask_str = 'field_mask()'
        else:
            obj_tag = 'HeapTag::Opaque'
            mask_str = 'kZeroMask'

        header_f.write("""
class %s {
 public:
  %s(Dict<BigStr*, value_asdl::value_t*>* attrs)""" % (spec_name, spec_name))

        if field_names:
            header_f.write('\n      : ')
            for i, field_name in enumerate(field_names):
                if i != 0:
                    header_f.write(',\n        ')
                header_f.write('%s(%s)' % (field_name, init_vals[i]))
        header_f.write(' {\n')
        header_f.write('  }\n')
        header_f.write('\n')

        for decl in field_decls:
            header_f.write('  %s\n' % decl)

        header_f.write('\n')
        header_f.write('  static constexpr ObjHeader obj_header() {\n')
        header_f.write('    return ObjHeader::Class(%s, %s, sizeof(%s));\n' %
                       (obj_tag, mask_str, spec_name))
        header_f.write('  }\n')

        if bits:
            header_f.write('\n')
            header_f.write('  static constexpr uint32_t field_mask() {\n')
            header_f.write('    return\n')
            header_f.write('      ')
            header_f.write('\n    | '.join(bits))
            header_f.write(';\n')
            header_f.write('  }\n')
            header_f.write('\n')

        header_f.write("""\
};
""")

    header_f.write("""
extern FlagSpec_c kFlagSpecs[];
extern FlagSpecAndMore_c kFlagSpecsAndMore[];

}  // namespace arg_types

#endif  // ARG_TYPES_H

""")

    cc_f.write("""\
// arg_types.cc is generated by frontend/flag_gen.py

#include "arg_types.h"
using runtime_asdl::flag_type_e;

namespace arg_types {

""")

    var_names = []
    for i, spec_name in enumerate(sorted(flag_spec.FLAG_SPEC)):
        spec = specs[spec_name]
        arity0_name = None
        arity1_name = None
        actions_long_name = None
        plus_name = None
        defaults_name = None

        if spec.arity0:
            arity0_name = 'arity0_%d' % i
            _WriteStrArray(cc_f, arity0_name, spec.arity0)

        if spec.arity1:
            arity1_name = 'arity1_%d' % i
            _WriteActions(cc_f, arity1_name, spec.arity1, counter)

        if spec.actions_long:
            actions_long_name = 'actions_long_%d' % i
            _WriteActions(cc_f, actions_long_name, spec.actions_long, counter)

        if spec.plus_flags:
            plus_name = 'plus_%d' % i
            _WriteStrArray(cc_f, plus_name, spec.plus_flags)

        if spec.defaults:
            defaults_name = 'defaults_%d' % i
            _WriteDefaults(cc_f, defaults_name, spec.defaults)

        var_names.append((arity0_name, arity1_name, actions_long_name,
                          plus_name, defaults_name))

    cc_f.write('FlagSpec_c kFlagSpecs[] = {\n')

    # Now print a table
    for i, spec_name in enumerate(sorted(flag_spec.FLAG_SPEC)):
        spec = specs[spec_name]
        names = var_names[i]
        cc_f.write('    { "%s", %s, %s, %s, %s, %s },\n' % (
            spec_name,
            names[0] or 'nullptr',
            names[1] or 'nullptr',
            names[2] or 'nullptr',
            names[3] or 'nullptr',
            names[4] or 'nullptr',
        ))

    cc_f.write("""\
    {},
};

""")

    n = len(var_names)
    var_names = []
    for i, spec_name in enumerate(sorted(flag_spec.FLAG_SPEC_AND_MORE)):
        spec = specs[spec_name]
        actions_short_name = None
        actions_long_name = None
        plus_name = None
        defaults_name = None

        if spec.actions_short:
            actions_short_name = 'short_%d' % (n + i)
            _WriteActions(cc_f, actions_short_name, spec.actions_short,
                          counter)

        #if spec.actions_long:
        if spec.actions_long:
            actions_long_name = 'long_%d' % (n + i)
            _WriteActions(cc_f, actions_long_name, spec.actions_long, counter)

        if spec.plus_flags:
            plus_name = 'plus_%d' % i
            _WriteStrArray(cc_f, plus_name, spec.plus_flags)

        if spec.defaults:
            defaults_name = 'defaults_%d' % (n + i)
            _WriteDefaults(cc_f, defaults_name, spec.defaults)

        var_names.append(
            (actions_short_name, actions_long_name, plus_name, defaults_name))

    cc_f.write('FlagSpecAndMore_c kFlagSpecsAndMore[] = {\n')
    for i, spec_name in enumerate(sorted(flag_spec.FLAG_SPEC_AND_MORE)):
        names = var_names[i]
        cc_f.write('    { "%s", %s, %s, %s, %s },\n' % (
            spec_name,
            names[0] or 'nullptr',
            names[1] or 'nullptr',
            names[2] or 'nullptr',
            names[3] or 'nullptr',
        ))

    cc_f.write("""\
    {},
};
""")

    cc_f.write("""\
}  // namespace arg_types
""")


def main(argv):
    try:
        action = argv[1]
    except IndexError:
        raise RuntimeError('Action required')

    if 0:
        for spec_name in sorted(flag_spec.FLAG_SPEC_AND_MORE):
            log('%s', spec_name)

    # Both kinds of specs have 'fields' attributes
    specs = {}
    specs.update(flag_spec.FLAG_SPEC)
    specs.update(flag_spec.FLAG_SPEC_AND_MORE)
    #log('SPECS %s', specs)

    for spec_name in sorted(specs):
        spec = specs[spec_name]
        #spec.spec.PrettyPrint(f=sys.stderr)
        #log('spec.arity1 %s', spec.spec.arity1)
        #log('%s', spec_name)

        #print(dir(spec))
        #print(spec.arity0)
        #print(spec.arity1)
        #print(spec.options)
        # Every flag has a default
        #log('%s', spec.fields)

    if action == 'cpp':
        prefix = argv[2]

        with open(prefix + '.h', 'w') as header_f:
            with open(prefix + '.cc', 'w') as cc_f:
                Cpp(specs, header_f, cc_f)

    elif action == 'mypy':
        print("""
from _devbuild.gen.value_asdl import value, value_e, value_t
from frontend.args import _Attributes
from mycpp import mops
from typing import cast, Dict, Optional
""")
        for spec_name in sorted(specs):
            spec = specs[spec_name]

            #log('%s spec.fields %s', spec_name, spec.fields)
            if not spec.fields:
                continue  # skip empty specs, e.g. eval

            print("""
class %s(object):
  def __init__(self, attrs):
    # type: (Dict[str, value_t]) -> None
""" % spec_name)

            i = 0
            for field_name in sorted(spec.fields):
                typ = spec.fields[field_name]
                field_name = field_name.replace('-', '_')

                with switch(typ) as case:
                    if case(flag_type_e.Bool):
                        print(
                            '    self.%s = cast(value.Bool, attrs[%r]).b  # type: bool'
                            % (field_name, field_name))

                    elif case(flag_type_e.Str):
                        tmp = 'val%d' % i
                        print('    %s = attrs[%r]' % (tmp, field_name))
                        print(
                            '    self.%s = None if %s.tag() == value_e.Undef else cast(value.Str, %s).s  # type: Optional[str]'
                            % (field_name, tmp, tmp))

                    elif case(flag_type_e.Int):
                        tmp = 'val%d' % i
                        print('    %s = attrs[%r]' % (tmp, field_name))
                        print(
                            '    self.%s = mops.BigInt(-1) if %s.tag() == value_e.Undef else cast(value.Int, %s).i  # type: mops.BigInt'
                            % (field_name, tmp, tmp))

                    elif case(flag_type_e.Float):
                        tmp = 'val%d' % i
                        print('    %s = attrs[%r]' % (tmp, field_name))
                        print(
                            '    self.%s = -1.0 if %s.tag() == value_e.Undef else cast(value.Float, %s).f  # type: float'
                            % (field_name, tmp, tmp))
                    else:
                        raise AssertionError(typ)

                i += 1

            print()

    else:
        raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
    try:
        main(sys.argv)
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
