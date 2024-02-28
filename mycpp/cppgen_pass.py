"""
cppgen.py - AST pass to that prints C++ code
"""
import io
import json  # for "C escaping"

from typing import overload, Union, Optional, Dict

import mypy
from mypy.visitor import ExpressionVisitor, StatementVisitor
from mypy.types import (Type, AnyType, NoneTyp, TupleType, Instance, NoneType,
                        Overloaded, CallableType, UnionType, UninhabitedType,
                        PartialType, TypeAliasType)
from mypy.nodes import (Expression, Statement, NameExpr, IndexExpr, MemberExpr,
                        TupleExpr, ExpressionStmt, IfStmt, StrExpr, SliceExpr,
                        FuncDef, UnaryExpr, OpExpr, ComparisonExpr, CallExpr,
                        IntExpr, ListExpr, DictExpr, ListComprehension)

from mycpp import format_strings
from mycpp.crash import catch_errors
from mycpp.util import log
from mycpp import util

from typing import Tuple, List

T = None

NAME_CONFLICTS = ('stdin', 'stdout', 'stderr')


class UnsupportedException(Exception):
    pass


def _SkipAssignment(var_name):
    """
    Skip at the top level:
      _ = log 
      unused1 = log

    Always skip:
      x, _ = mytuple  # no second var
    """
    return var_name == '_' or var_name.startswith('unused')


def _GetCTypeForCast(type_expr):
    """ MyPy cast() """

    if isinstance(type_expr, MemberExpr):
        subtype_name = '%s::%s' % (type_expr.expr.name, type_expr.name)
    elif isinstance(type_expr, IndexExpr):
        # List[word_t] would be a problem.
        # But worked around it in osh/word_parse.py
        #subtype_name = 'List<word_t>'
        raise AssertionError()
    elif isinstance(type_expr, StrExpr):
        parts = type_expr.value.split('.')
        subtype_name = '::'.join(parts)
    else:
        subtype_name = type_expr.name

    # Hack for now
    if subtype_name != 'int' and subtype_name != 'mops::BigInt':
        subtype_name += '*'
    return subtype_name


def _GetCastKind(module_path, cast_to_type):
    """Translate MyPy cast to C++ cast.

    Prefer static_cast, but sometimes we need reinterpret_cast.
    """
    cast_kind = 'static_cast'

    # Hack for Id.Expr_CastedDummy in expr_to_ast.py
    if 'expr_to_ast.py' in module_path:
        for name in (
                'ShArrayLiteral',
                'CommandSub',
                'BracedVarSub',
                'DoubleQuoted',
                'SingleQuoted',
                # Another kind of hack, not because of CastDummy
                'y_lhs_t',
        ):
            if name in cast_to_type:
                cast_kind = 'reinterpret_cast'
                break

    # The other side of Id.Expr_CastedDummy
    if 'expr_parse.py' in module_path:
        for name in ('Token', ):
            if name in cast_to_type:
                cast_kind = 'reinterpret_cast'
                break

    if 'process.py' in module_path and 'mylib::Writer' in cast_to_type:
        cast_kind = 'reinterpret_cast'

    return cast_kind


def _GetContainsFunc(t):
    """ x in y """
    contains_func = None

    if isinstance(t, Instance):
        type_name = t.type.fullname

        if type_name == 'builtins.list':
            contains_func = 'list_contains'

        elif type_name == 'builtins.str':
            contains_func = 'str_contains'

        elif type_name == 'builtins.dict':
            contains_func = 'dict_contains'

    elif isinstance(t, UnionType):
        # Special case for Optional[T] == Union[T, None]
        if len(t.items) != 2:
            raise NotImplementedError('Expected Optional, got %s' % t)

        if not isinstance(t.items[1], NoneTyp):
            raise NotImplementedError('Expected Optional, got %s' % t)

        contains_func = _GetContainsFunc(t.items[0])

    return contains_func  # None checked later


def IsStr(t):
    """Helper to check if a type is a string."""
    return isinstance(t, Instance) and t.type.fullname == 'builtins.str'


def _EqualsFunc(left_type):
    if IsStr(left_type):
        return 'str_equals'

    if (isinstance(left_type, UnionType) and len(left_type.items) == 2 and
            IsStr(left_type.items[0]) and
            isinstance(left_type.items[1], NoneTyp)):
        return 'maybe_str_equals'

    return None


_EXPLICIT = ('builtins.str', 'builtins.list', 'builtins.dict')


def _CheckCondition(node, types):
    """
    Ban
        if (mystr)
        if (mylist)
        if (mydict)

    They mean non-empty in Python.
    """
    #log('NODE %s', node)

    if isinstance(node, UnaryExpr) and node.op == 'not':
        return _CheckCondition(node.expr, types)

    if isinstance(node, OpExpr):
        #log('OpExpr node %s %s', node, dir(node))

        # if x > 0 and not mylist, etc.
        return _CheckCondition(node.left, types) and _CheckCondition(
            node.right, types)

    t = types[node]

    if isinstance(t, Instance):
        type_name = t.type.fullname
        if type_name in _EXPLICIT:
            return False

    elif isinstance(t, UnionType):
        if len(t.items) == 2 and isinstance(t.items[1], NoneTyp):
            t2 = t.items[0]
            if t2.type.fullname in _EXPLICIT:
                return False

    return True


def CTypeIsManaged(c_type):
    # type: (str) -> bool
    """For rooting and field masks."""
    assert c_type != 'void'

    if util.SMALL_STR:
        if c_type == 'Str':
            return True

    # int, double, bool, scope_t enums, etc. are not managed
    return c_type.endswith('*')


def GetCType(t, param=False, local=False):
    """Recursively translate MyPy type to C++ type."""
    is_pointer = False

    if isinstance(t, NoneTyp):  # e.g. a function that doesn't return anything
        return 'void'

    elif isinstance(t, AnyType):
        # Note: this usually results in another compile-time error.  We should get
        # rid of the 'Any' types.
        c_type = 'void'
        is_pointer = True

    elif isinstance(t, PartialType):
        # Note: bin/oil.py has some of these?  Not sure why.
        c_type = 'void'
        is_pointer = True

    # TODO: It seems better not to check for string equality, but that's what
    # mypyc/genops.py does?

    elif isinstance(t, Instance):
        type_name = t.type.fullname
        #log('** TYPE NAME %s', type_name)

        if type_name == 'builtins.int':
            c_type = 'int'

        elif type_name == 'builtins.float':
            c_type = 'double'

        elif type_name == 'builtins.bool':
            c_type = 'bool'

        elif type_name == 'builtins.str':
            if util.SMALL_STR:
                c_type = 'Str'
                is_pointer = False
            else:
                c_type = 'BigStr'
                is_pointer = True

        elif type_name == 'builtins.list':
            assert len(t.args) == 1, t.args
            type_param = t.args[0]
            inner_c_type = GetCType(type_param)
            c_type = 'List<%s>' % inner_c_type
            is_pointer = True

        elif type_name == 'builtins.dict':
            params = []
            for type_param in t.args:
                params.append(GetCType(type_param))
            c_type = 'Dict<%s>' % ', '.join(params)
            is_pointer = True

        elif 'BigInt' in type_name:
            # also spelled mycpp.mylib.BigInt

            c_type = 'mops::BigInt'
            # Not a pointer!

        elif type_name == 'typing.IO':
            c_type = 'mylib::File'
            is_pointer = True

        elif type_name == 'typing.Iterator':
            assert len(t.args) == 1, t.args
            type_param = t.args[0]
            inner_c_type = GetCType(type_param)
            c_type = 'ListIter<%s>' % inner_c_type

        else:
            # note: fullname => 'parse.Lexer'; name => 'Lexer'
            base_class_names = [b.type.fullname for b in t.type.bases]

            #log('** base_class_names %s', base_class_names)

            # Check base class for pybase.SimpleObj so we can output
            # expr_asdl::tok_t instead of expr_asdl::tok_t*.  That is a enum, while
            # expr_t is a "regular base class".
            # NOTE: Could we avoid the typedef?  If it's SimpleObj, just generate
            # tok_e instead?

            if 'asdl.pybase.SimpleObj' not in base_class_names:
                is_pointer = True

            parts = t.type.fullname.split('.')
            c_type = '%s::%s' % (parts[-2], parts[-1])

    elif isinstance(t, UninhabitedType):
        # UninhabitedType has a NoReturn flag
        c_type = 'void'

    elif isinstance(t, TupleType):
        inner_c_types = []
        for inner_type in t.items:
            c_type = GetCType(inner_type)
            if c_type == 'void':
                # Why does MyPy give us 'None' instead of type declared with type: ?
                # log('**** items %s', t.items)
                pass
            inner_c_types.append(c_type)

        c_type = 'Tuple%d<%s>' % (len(t.items), ', '.join(inner_c_types))
        is_pointer = True

    elif isinstance(t, UnionType):
        # Special case for Optional[T] == Union[T, None]
        if len(t.items) != 2:
            raise NotImplementedError('Expected 2 items in Union, got %s' %
                                      len(t.items))

        t0 = t.items[0]
        t1 = t.items[1]

        c_type = None
        if isinstance(t1, NoneTyp):  # Optional[T0]
            c_type = GetCType(t.items[0])
        else:
            # Detect type alias defined in core/error.py
            # IOError_OSError = Union[IOError, OSError]
            t0_name = t0.type.fullname
            t1_name = t1.type.fullname
            if t0_name == 'builtins.IOError' and t1_name == 'builtins.OSError':
                c_type = 'IOError_OSError'
                is_pointer = True

        if c_type is None:
            raise NotImplementedError('Unexpected Union type %s' % t)

    elif isinstance(t, CallableType):
        # Function types are expanded
        #    Callable[[Parser, Token, int], arith_expr_t]
        # -> arith_expr_t* (*f)(Parser*, Token*, int) nud;

        ret_type = GetCType(t.ret_type)
        arg_types = [GetCType(typ) for typ in t.arg_types]
        c_type = '%s (*f)(%s)' % (ret_type, ', '.join(arg_types))

    elif isinstance(t, TypeAliasType):
        if 0:
            log('***')
            log('%s', t)
            log('%s', dir(t))
            log('%s', t.alias)
            log('%s', dir(t.alias))
            log('%s', t.alias.target)
            log('***')
        return GetCType(t.alias.target)

    else:
        raise NotImplementedError('MyPy type: %s %s' % (type(t), t))

    if is_pointer:
        if param or local:
            c_type = 'Local<%s>' % c_type
        else:
            c_type += '*'

    return c_type


def GetCReturnType(t) -> Tuple[str, bool, Optional[str]]:
    """
  Returns a C string, whether the tuple-by-value optimization was applied, and
  the C type of an extra output param if the function is a generator.
  """

    c_ret_type = GetCType(t)

    # Optimization: Return tupels BY VALUE
    if isinstance(t, TupleType):
        assert c_ret_type.endswith('*')
        return c_ret_type[:-1], True, None
    elif c_ret_type.startswith('ListIter<'):
        assert len(t.args) == 1, t.args
        inner_c_type = GetCType(t.args[0])
        return 'void', False, 'List<%s>*' % inner_c_type
    else:
        return c_ret_type, False, None


def PythonStringLiteral(s: str) -> str:
    """
  Returns a properly quoted string.
  """
    # MyPy does bad escaping. Decode and push through json to get something
    # workable in C++.
    return json.dumps(format_strings.DecodeMyPyString(s))


class Generate(ExpressionVisitor[T], StatementVisitor[None]):

    def __init__(self,
                 types: Dict[Expression, Type],
                 const_lookup,
                 f,
                 virtual=None,
                 local_vars=None,
                 fmt_ids=None,
                 field_gc=None,
                 decl=False,
                 forward_decl=False,
                 stack_roots_warn=None):
        self.types = types
        self.const_lookup = const_lookup
        self.f = f

        self.virtual = virtual
        # local_vars: FuncDef node -> list of type, var
        # This is different from member_vars because we collect it in the 'decl'
        # phase.  But then write it in the definition phase.
        self.local_vars = local_vars
        self.fmt_ids = fmt_ids
        self.field_gc = field_gc
        self.fmt_funcs = io.StringIO()

        self.decl = decl
        self.forward_decl = forward_decl
        self.stack_roots_warn = stack_roots_warn

        self.unique_id = 0

        self.indent = 0
        self.local_var_list = []  # Collected at assignment
        self.prepend_to_block = None  # For writing vars after {
        self.current_func_node = None
        self.current_stmt_node = None
        # Temporary lists to use as output params for generators
        self.yield_accumulators = {
        }  # type: Dict[Union[Statement, FuncDef], Tuple[str, str]]

        # This is cleared when we start visiting a class.  Then we visit all the
        # methods, and accumulate the types of everything that looks like
        # self.foo = 1.  Then we write C++ class member declarations at the end
        # of the class.
        # This is all in the 'decl' phase.
        self.member_vars: Dict[str, Type] = {}

        self.current_class_name = None  # for prototypes
        self.current_method_name = None

        self.imported_names = set()  # MemberExpr -> module::Foo() or self->foo

        # HACK for conditional import inside mylib.PYTHON
        # in core/shell.py
        self.imported_names.add('help_meta')

        # So we can report multiple at once
        # module path, line number, message
        self.errors_keep_going: List[Tuple[str, int, str]] = []

        self.writing_default_arg = False

    def log(self, msg, *args):
        ind_str = self.indent * '  '
        log(ind_str + msg, *args)

    def always_write(self, msg, *args):
        """Write unconditionally - forward decl, decl, def """
        if args:
            msg = msg % args
        self.f.write(msg)

    def always_write_ind(self, msg, *args):
        ind_str = self.indent * '  '
        self.always_write(ind_str + msg, *args)

    def def_write(self, msg, *args):
        """Write only in definitions."""

        if self.forward_decl:
            return

        if self.decl and not self.writing_default_arg:
            return

        if args:
            msg = msg % args
        self.f.write(msg)

    def def_write_ind(self, msg, *args):
        ind_str = self.indent * '  '
        self.def_write(ind_str + msg, *args)

    def decl_write(self, msg, *args):
        """Write only in the decl stage (not forward declarations)"""
        if not self.decl:
            return

        if args:
            msg = msg % args
        self.f.write(msg)

    def decl_write_ind(self, msg, *args):
        ind_str = self.indent * '  '
        self.decl_write(ind_str + msg, *args)

    #
    # COPIED from IRBuilder
    #

    @overload
    def accept(self, node: Expression) -> T:
        ...

    @overload
    def accept(self, node: Statement) -> None:
        ...

    def accept(self, node: Union[Statement, Expression]) -> Optional[T]:
        with catch_errors(self.module_path, node.line):
            if isinstance(node, Expression):
                try:
                    res = node.accept(self)
                    #res = self.coerce(res, self.node_type(node), node.line)

                # If we hit an error during compilation, we want to
                # keep trying, so we can produce more error
                # messages. Generate a temp of the right type to keep
                # from causing more downstream trouble.
                except UnsupportedException:
                    res = self.alloc_temp(self.node_type(node))
                return res
            else:
                try:
                    node.accept(self)
                except UnsupportedException:
                    pass
                return None

    def report_error(self, node: Union[Statement, Expression], msg: str):
        err = (self.module_path, node.line, msg)
        self.errors_keep_going.append(err)

    # Not in superclasses:

    def visit_mypy_file(self, o: 'mypy.nodes.MypyFile') -> T:
        # Skip some stdlib stuff.  A lot of it is brought in by 'import
        # typing'.
        if o.fullname in ('__future__', 'sys', 'types', 'typing', 'abc',
                          '_ast', 'ast', '_weakrefset', 'collections',
                          'cStringIO', 're', 'builtins'):

            # These module are special; their contents are currently all
            # built-in primitives.
            return

        #self.log('')
        #self.log('mypyfile %s', o.fullname)

        mod_parts = o.fullname.split('.')
        if self.forward_decl:
            comment = 'forward declare'
        elif self.decl:
            comment = 'declare'
        else:
            comment = 'define'

        self.always_write_ind('namespace %s {  // %s\n', mod_parts[-1],
                              comment)
        self.always_write('\n')

        self.module_path = o.path

        if self.forward_decl:
            self.indent += 1

        #self.log('defs %s', o.defs)
        for node in o.defs:
            # skip module docstring
            if (isinstance(node, ExpressionStmt) and
                    isinstance(node.expr, StrExpr)):
                continue
            self.accept(node)

        # Write fmtX() functions inside the namespace.
        if self.decl:
            self.always_write('\n')
            self.always_write(self.fmt_funcs.getvalue())
            self.fmt_funcs = io.StringIO()  # clear it for the next file

        if self.forward_decl:
            self.indent -= 1

        self.always_write('\n')
        self.always_write_ind('}  // %s namespace %s\n', comment,
                              mod_parts[-1])
        self.always_write('\n')

        for path, line_num, msg in self.errors_keep_going:
            self.log('%s:%s %s', path, line_num, msg)

    # NOTE: Copied ExpressionVisitor and StatementVisitor nodes below!

    # LITERALS

    def visit_int_expr(self, o: 'mypy.nodes.IntExpr') -> T:
        self.def_write(str(o.value))

    def visit_str_expr(self, o: 'mypy.nodes.StrExpr') -> T:
        self.def_write(self.const_lookup[o])

    def visit_bytes_expr(self, o: 'mypy.nodes.BytesExpr') -> T:
        pass

    def visit_unicode_expr(self, o: 'mypy.nodes.UnicodeExpr') -> T:
        pass

    def visit_float_expr(self, o: 'mypy.nodes.FloatExpr') -> T:
        # e.g. for arg.t > 0.0
        self.def_write(str(o.value))

    def visit_complex_expr(self, o: 'mypy.nodes.ComplexExpr') -> T:
        pass

    # Expressions

    def visit_ellipsis(self, o: 'mypy.nodes.EllipsisExpr') -> T:
        pass

    def visit_star_expr(self, o: 'mypy.nodes.StarExpr') -> T:
        pass

    def visit_name_expr(self, o: 'mypy.nodes.NameExpr') -> T:
        if o.name == 'None':
            self.def_write('nullptr')
            return
        if o.name == 'True':
            self.def_write('true')
            return
        if o.name == 'False':
            self.def_write('false')
            return
        if o.name == 'self':
            self.def_write('this')
            return

        if o.name in NAME_CONFLICTS:
            self.report_error(
                o,
                "The name %r conflicts with C macros on some platforms; choose a different name"
                % o.name)
            return

        self.def_write(o.name)

    def visit_member_expr(self, o: 'mypy.nodes.MemberExpr') -> T:
        if o.expr:
            # Why do we not get some of the types?  e.g. hnode.Record in asdl/runtime
            # But this might suffice for the "Str_v" and "value_v" refactoring.
            # We want to rewrite w.parts not to w->parts, but to w.parts() (method call)

            is_small_str = False
            if util.SMALL_STR:
                lhs_type = self.types.get(o.expr)
                if IsStr(lhs_type):
                    is_small_str = True
                else:
                    #self.log('NOT a string %s %s', o.expr, o.name)
                    pass
                """
                if lhs_type is not None and isinstance(lhs_type, Instance):
                    self.log('lhs_type %s expr %s name %s',
                             lhs_type.type.fullname, o.expr, o.name)

                 """

            is_asdl = o.name == 'CreateNull'  # hack for MyType.CreateNull(alloc_lists=True)
            is_module = (isinstance(o.expr, NameExpr) and
                         o.expr.name in self.imported_names)

            # This is an approximate hack that assumes that locals don't shadow
            # imported names.  Might be a problem with names like 'word'?
            if is_small_str:
                op = '.'
            elif is_asdl or is_module:
                op = '::'
            else:
                op = '->'  # Everything is a pointer

            self.accept(o.expr)
            self.def_write(op)

        if o.name == 'errno':
            # e->errno -> e->errno_ to avoid conflict with C macro
            self.def_write('errno_')
        elif o.name in NAME_CONFLICTS:
            self.report_error(
                o,
                "The name %r conflicts with C macros on some platforms; choose a different name"
                % o.name)
        else:
            self.def_write('%s', o.name)

    def visit_yield_from_expr(self, o: 'mypy.nodes.YieldFromExpr') -> T:
        pass

    def visit_yield_expr(self, o: 'mypy.nodes.YieldExpr') -> T:
        assert self.current_func_node in self.yield_accumulators
        self.def_write_ind('%s->append(',
                           self.yield_accumulators[self.current_func_node][0])
        self.accept(o.expr)
        self.def_write(');\n')

    def _WriteArgList(self, o):
        self.def_write('(')
        for i, arg in enumerate(o.args):
            if i != 0:
                self.def_write(', ')
            self.accept(arg)

        # Will be set if we're:
        # a) accumulating the output of an iterator
        # b) constructing an iterator with the result of (a)
        if self.current_stmt_node in self.yield_accumulators:
            if len(o.args) > 0:
                self.def_write(', ')

            arg_name, _ = self.yield_accumulators[self.current_stmt_node]
            self.def_write('&%s', arg_name)

        self.def_write(')')

    def _IsInstantiation(self, o):
        callee_name = o.callee.name
        callee_type = self.types[o.callee]

        # e.g. int() takes str, float, etc.  It doesn't matter for translation.
        if isinstance(callee_type, Overloaded):
            if 0:
                for item in callee_type.items():
                    self.log('item: %s', item)

        if isinstance(callee_type, CallableType):
            # If the function name is the same as the return type, then add
            # 'Alloc<>'.  f = Foo() => f = Alloc<Foo>().
            ret_type = callee_type.ret_type

            # str(i) doesn't need new.  For now it's a free function.
            # TODO: rename int_to_str?  or BigStr::from_int()?
            if (callee_name not in ('str', 'bool', 'float') and
                    'BigInt' not in callee_name and
                    isinstance(ret_type, Instance)):

                ret_type_name = ret_type.type.name

                # HACK: Const is the callee; expr.Const is the return type
                if (ret_type_name == callee_name or
                        ret_type_name.endswith('__' + callee_name)):
                    return True

        return False

    def visit_call_expr(self, o: 'mypy.nodes.CallExpr') -> T:
        if o.callee.name == 'isinstance':
            assert len(o.args) == 2, o.args
            obj = o.args[0]
            typ = o.args[1]

            if 0:
                log('obj %s', obj)
                log('typ %s', typ)

            self.accept(obj)
            self.def_write('->tag() == ')
            assert isinstance(typ, NameExpr), typ

            # source__CFlag -> source_e::CFlag
            tag = typ.name.replace('__', '_e::')
            self.def_write(tag)
            return

        #    return cast(ShArrayLiteral, tok)
        # -> return static_cast<ShArrayLiteral*>(tok)

        # TODO: Consolidate this with AssignmentExpr logic.

        if o.callee.name == 'cast':
            call = o
            type_expr = call.args[0]

            subtype_name = _GetCTypeForCast(type_expr)
            cast_kind = _GetCastKind(self.module_path, subtype_name)
            self.def_write('%s<%s>(', cast_kind, subtype_name)
            self.accept(call.args[1])  # variable being casted
            self.def_write(')')
            return

        # Translate printf-style varargs:
        #
        # log('foo %s', x)
        #   =>
        # log(StrFormat('foo %s', x))
        if o.callee.name == 'log':
            args = o.args
            if len(args) == 1:  # log(CONST)
                self.def_write('mylib::print_stderr(')
                self.accept(args[0])
                self.def_write(')')
                return

            quoted_fmt = PythonStringLiteral(args[0].value)

            # DEFINITION PASS
            self.def_write('mylib::print_stderr(StrFormat(%s, ' % quoted_fmt)
            for i, arg in enumerate(args[1:]):
                if i != 0:
                    self.def_write(', ')
                self.accept(arg)
            self.def_write('))')
            return

        callee_name = o.callee.name

        if isinstance(o.callee, MemberExpr) and callee_name == 'next':
            self.accept(o.callee.expr)
            self.def_write('.iterNext')
            self._WriteArgList(o)
            return

        if self._IsInstantiation(o):
            self.def_write('Alloc<')
            self.accept(o.callee)
            self.def_write('>')
            self._WriteArgList(o)
            return

        # Namespace.
        if callee_name == 'int':  # int('foo') in Python conflicts with keyword
            self.def_write('to_int')
        elif callee_name == 'float':
            self.def_write('to_float')
        elif callee_name == 'bool':
            self.def_write('to_bool')
        else:
            self.accept(o.callee)  # could be f() or obj.method()

        self._WriteArgList(o)

        # TODO: look at keyword arguments!
        #self.log('  arg_kinds %s', o.arg_kinds)
        #self.log('  arg_names %s', o.arg_names)

    def visit_op_expr(self, o: 'mypy.nodes.OpExpr') -> T:
        # a + b when a and b are strings.  (Can't use operator overloading
        # because they're pointers.)
        left_type = self.types[o.left]
        right_type = self.types[o.right]

        # NOTE: Need GetCType to handle Optional[BigStr*] in ASDL schemas.
        # Could tighten it up later.
        left_ctype = GetCType(left_type)
        right_ctype = GetCType(right_type)

        c_op = o.op
        if left_ctype == right_ctype == 'int' and c_op == '//':
            # integer division // -> /
            c_op = '/'

        # 'abc' + 'def'
        if left_ctype == right_ctype == 'BigStr*' and c_op == '+':
            self.def_write('str_concat(')
            self.accept(o.left)
            self.def_write(', ')
            self.accept(o.right)
            self.def_write(')')
            return

        # 'abc' * 3
        if left_ctype == 'BigStr*' and right_ctype == 'int' and c_op == '*':
            self.def_write('str_repeat(')
            self.accept(o.left)
            self.def_write(', ')
            self.accept(o.right)
            self.def_write(')')
            return

        # [None] * 3  =>  list_repeat(None, 3)
        if left_ctype.startswith(
                'List<') and right_ctype == 'int' and c_op == '*':
            self.def_write('list_repeat(')
            self.accept(o.left.items[0])
            self.def_write(', ')
            self.accept(o.right)
            self.def_write(')')
            return

        # RHS can be primitive or tuple
        if left_ctype == 'BigStr*' and c_op == '%':
            self.def_write('StrFormat(')
            if isinstance(o.left, StrExpr):
                self.def_write(PythonStringLiteral(o.left.value))
            else:
                self.accept(o.left)
            #log('right_type %s', right_type)
            if isinstance(right_type, Instance):
                fmt_types = [right_type]
            elif isinstance(right_type, TupleType):
                fmt_types = right_type.items
            # Handle Optional[str]
            elif (isinstance(right_type, UnionType) and
                  len(right_type.items) == 2 and
                  isinstance(right_type.items[1], NoneTyp)):
                fmt_types = [right_type.items[0]]
            else:
                raise AssertionError(right_type)

            # In the definition pass, write the call site.
            if isinstance(right_type, TupleType):
                for i, item in enumerate(o.right.items):
                    self.def_write(', ')
                    self.accept(item)
            else:  # '[%s]' % x
                self.def_write(', ')
                self.accept(o.right)

            self.def_write(')')
            return

        # These parens are sometimes extra, but sometimes required.  Example:
        #
        # if ((a and (false or true))) {  # right
        # vs.
        # if (a and false or true)) {  # wrong
        self.def_write('(')
        self.accept(o.left)
        self.def_write(' %s ', c_op)
        self.accept(o.right)
        self.def_write(')')

    def visit_comparison_expr(self, o: 'mypy.nodes.ComparisonExpr') -> T:
        # Make sure it's binary
        assert len(o.operators) == 1, o.operators
        assert len(o.operands) == 2, o.operands

        operator = o.operators[0]
        left = o.operands[0]
        right = o.operands[1]

        # Assume is and is not are for None / nullptr comparison.
        if operator == 'is':  # foo is None => foo == nullptr
            self.accept(o.operands[0])
            self.def_write(' == ')
            self.accept(o.operands[1])
            return

        if operator == 'is not':  # foo is not None => foo != nullptr
            self.accept(o.operands[0])
            self.def_write(' != ')
            self.accept(o.operands[1])
            return

        # TODO: Change Optional[T] to T for our purposes?
        t0 = self.types[left]
        t1 = self.types[right]

        # 0: not a special case
        # 1: str
        # 2: Optional[str] which is Union[str, None]
        left_type = 0  # not a special case
        right_type = 0  # not a special case

        if IsStr(t0):
            left_type = 1
        elif (isinstance(t0, UnionType) and len(t0.items) == 2 and
              IsStr(t0.items[0]) and isinstance(t0.items[1], NoneTyp)):
            left_type = 2

        if IsStr(t1):
            right_type = 1
        elif (isinstance(t1, UnionType) and len(t1.items) == 2 and
              IsStr(t1.items[0]) and isinstance(t1.items[1], NoneTyp)):
            right_type = 2

        #self.log('left_type %s right_type %s', left_type, right_type)

        if left_type > 0 and right_type > 0 and operator in ('==', '!='):
            if operator == '!=':
                self.def_write('!(')

            # NOTE: This could also be str_equals(left, right)?  Does it make a
            # difference?
            if left_type > 1 or right_type > 1:
                self.def_write('maybe_str_equals(')
            else:
                self.def_write('str_equals(')
            self.accept(left)
            self.def_write(', ')
            self.accept(right)
            self.def_write(')')

            if operator == '!=':
                self.def_write(')')
            return

        # Note: we could get rid of this altogether and rely on C++ function
        # overloading.  But somehow I like it more explicit, closer to C (even
        # though we use templates).
        contains_func = _GetContainsFunc(t1)

        if operator == 'in':
            if isinstance(right, TupleExpr):
                left_type = self.types[left]

                equals_func = _EqualsFunc(left_type)

                # x in (1, 2, 3) => (x == 1 || x == 2 || x == 3)
                self.def_write('(')

                for i, item in enumerate(right.items):
                    if i != 0:
                        self.def_write(' || ')

                    if equals_func:
                        self.def_write('%s(' % equals_func)
                        self.accept(left)
                        self.def_write(', ')
                        self.accept(item)
                        self.def_write(')')
                    else:
                        self.accept(left)
                        self.def_write(' == ')
                        self.accept(item)

                self.def_write(')')
                return

            assert contains_func, "RHS of 'in' has type %r" % t1
            # x in mylist => list_contains(mylist, x)
            self.def_write('%s(', contains_func)
            self.accept(right)
            self.def_write(', ')
            self.accept(left)
            self.def_write(')')
            return

        if operator == 'not in':
            if isinstance(right, TupleExpr):
                left_type = self.types[left]
                equals_func = _EqualsFunc(left_type)

                # x not in (1, 2, 3) => (x != 1 && x != 2 && x != 3)
                self.def_write('(')

                for i, item in enumerate(right.items):
                    if i != 0:
                        self.def_write(' && ')

                    if equals_func:
                        self.def_write('!%s(' % equals_func)
                        self.accept(left)
                        self.def_write(', ')
                        self.accept(item)
                        self.def_write(')')
                    else:
                        self.accept(left)
                        self.def_write(' != ')
                        self.accept(item)

                self.def_write(')')
                return

            assert contains_func, t1

            # x not in mylist => !list_contains(mylist, x)
            self.def_write('!%s(', contains_func)
            self.accept(right)
            self.def_write(', ')
            self.accept(left)
            self.def_write(')')
            return

        # Default case
        self.accept(o.operands[0])
        self.def_write(' %s ', o.operators[0])
        self.accept(o.operands[1])

    def visit_cast_expr(self, o: 'mypy.nodes.CastExpr') -> T:
        pass

    def visit_reveal_expr(self, o: 'mypy.nodes.RevealExpr') -> T:
        pass

    def visit_super_expr(self, o: 'mypy.nodes.SuperExpr') -> T:
        pass

    def visit_assignment_expr(self, o: 'mypy.nodes.AssignmentExpr') -> T:
        pass

    def visit_unary_expr(self, o: 'mypy.nodes.UnaryExpr') -> T:
        # e.g. a[-1] or 'not x'
        if o.op == 'not':
            op_str = '!'
        else:
            op_str = o.op
        self.def_write(op_str)
        self.accept(o.expr)

    def _WriteListElements(self, items, sep=', '):
        # sep may be 'COMMA' for a macro
        self.def_write('{')
        for i, item in enumerate(items):
            if i != 0:
                self.def_write(sep)
            self.accept(item)
        self.def_write('}')

    def visit_list_expr(self, o: 'mypy.nodes.ListExpr') -> T:
        list_type = self.types[o]
        #self.log('**** list_type = %s', list_type)
        c_type = GetCType(list_type)

        item_type = list_type.args[0]  # int for List[int]
        item_c_type = GetCType(item_type)

        assert c_type.endswith('*'), c_type
        c_type = c_type[:-1]  # HACK TO CLEAN UP

        if len(o.items) == 0:
            self.def_write('Alloc<%s>()' % c_type)
        else:
            self.def_write('NewList<%s>(std::initializer_list<%s>' %
                           (item_c_type, item_c_type))
            self._WriteListElements(o.items)
            self.def_write(')')

    def visit_dict_expr(self, o: 'mypy.nodes.DictExpr') -> T:
        dict_type = self.types[o]
        c_type = GetCType(dict_type)
        assert c_type.endswith('*'), c_type
        c_type = c_type[:-1]  # HACK TO CLEAN UP

        key_type, val_type = dict_type.args
        key_c_type = GetCType(key_type)
        val_c_type = GetCType(val_type)

        self.def_write('Alloc<%s>(' % c_type)
        #self.def_write('NewDict<%s, %s>(' % (key_c_type, val_c_type))
        if o.items:
            keys = [k for k, _ in o.items]
            values = [v for _, v in o.items]

            self.def_write('std::initializer_list<%s>' % key_c_type)
            self._WriteListElements(keys)
            self.def_write(', ')

            self.def_write('std::initializer_list<%s>' % val_c_type)
            self._WriteListElements(values)

        self.def_write(')')

    def visit_tuple_expr(self, o: 'mypy.nodes.TupleExpr') -> T:
        tuple_type = self.types[o]
        c_type = GetCType(tuple_type)
        assert c_type.endswith('*'), c_type
        c_type = c_type[:-1]  # HACK TO CLEAN UP

        self.def_write('(Alloc<%s>(' % c_type)
        for i, item in enumerate(o.items):
            if i != 0:
                self.def_write(', ')
            self.accept(item)
        self.def_write('))')

    def visit_set_expr(self, o: 'mypy.nodes.SetExpr') -> T:
        pass

    def visit_index_expr(self, o: 'mypy.nodes.IndexExpr') -> T:
        self.accept(o.base)

        #base_type = self.types[o.base]
        #self.log('*** BASE TYPE %s', base_type)

        if isinstance(o.index, SliceExpr):
            self.accept(o.index)  # method call
        else:
            # it's hard syntactically to do (*a)[0], so do it this way.
            if util.SMALL_STR:
                self.def_write('.at(')
            else:
                self.def_write('->at(')

            self.accept(o.index)
            self.def_write(')')

    def visit_type_application(self, o: 'mypy.nodes.TypeApplication') -> T:
        pass

    def visit_lambda_expr(self, o: 'mypy.nodes.LambdaExpr') -> T:
        pass

    def visit_list_comprehension(self, o: 'mypy.nodes.ListComprehension') -> T:
        pass

    def visit_set_comprehension(self, o: 'mypy.nodes.SetComprehension') -> T:
        pass

    def visit_dictionary_comprehension(
            self, o: 'mypy.nodes.DictionaryComprehension') -> T:
        pass

    def visit_generator_expr(self, o: 'mypy.nodes.GeneratorExpr') -> T:
        pass

    def visit_slice_expr(self, o: 'mypy.nodes.SliceExpr') -> T:
        self.def_write('->slice(')
        if o.begin_index:
            self.accept(o.begin_index)
        else:
            self.def_write('0')  # implicit beginning

        if o.end_index:
            self.def_write(', ')
            self.accept(o.end_index)

        if o.stride:
            if not o.begin_index or not o.end_index:
                raise AssertionError(
                    'Stride only supported with beginning and ending index')

            self.def_write(', ')
            self.accept(o.stride)

        self.def_write(')')

    def visit_conditional_expr(self, o: 'mypy.nodes.ConditionalExpr') -> T:
        if not _CheckCondition(o.cond, self.types):
            self.report_error(
                o,
                "Use explicit len(obj) or 'obj is not None' for mystr, mylist, mydict"
            )
            return

        # 0 if b else 1 -> b ? 0 : 1
        self.accept(o.cond)
        self.def_write(' ? ')
        self.accept(o.if_expr)
        self.def_write(' : ')
        self.accept(o.else_expr)

    def visit_backquote_expr(self, o: 'mypy.nodes.BackquoteExpr') -> T:
        pass

    def visit_type_var_expr(self, o: 'mypy.nodes.TypeVarExpr') -> T:
        pass

    def visit_type_alias_expr(self, o: 'mypy.nodes.TypeAliasExpr') -> T:
        pass

    def visit_namedtuple_expr(self, o: 'mypy.nodes.NamedTupleExpr') -> T:
        pass

    def visit_enum_call_expr(self, o: 'mypy.nodes.EnumCallExpr') -> T:
        pass

    def visit_typeddict_expr(self, o: 'mypy.nodes.TypedDictExpr') -> T:
        pass

    def visit_newtype_expr(self, o: 'mypy.nodes.NewTypeExpr') -> T:
        pass

    def visit__promote_expr(self, o: 'mypy.nodes.PromoteExpr') -> T:
        pass

    def visit_await_expr(self, o: 'mypy.nodes.AwaitExpr') -> T:
        pass

    def visit_temp_node(self, o: 'mypy.nodes.TempNode') -> T:
        pass

    def _write_tuple_unpacking(self,
                               temp_name,
                               lval_items,
                               item_types,
                               is_return=False):
        """Used by assignment and for loops."""
        for i, (lval_item, item_type) in enumerate(zip(lval_items,
                                                       item_types)):
            #self.log('*** %s :: %s', lval_item, item_type)
            if isinstance(lval_item, NameExpr):
                if _SkipAssignment(lval_item.name):
                    continue

                item_c_type = GetCType(item_type)
                # declare it at the top of the function
                if self.decl:
                    self.local_var_list.append((lval_item.name, item_c_type))
                self.def_write_ind('%s', lval_item.name)
            else:
                # Could be MemberExpr like self.foo, self.bar = baz
                self.def_write_ind('')
                self.accept(lval_item)

            # Tuples that are return values aren't pointers
            op = '.' if is_return else '->'
            self.def_write(' = %s%sat%d();\n', temp_name, op, i)  # RHS

    def visit_assignment_stmt(self, o: 'mypy.nodes.AssignmentStmt') -> T:
        # Declare constant strings.  They have to be at the top level.
        if self.decl and self.indent == 0 and len(o.lvalues) == 1:
            lval = o.lvalues[0]
            c_type = GetCType(self.types[lval])
            if not _SkipAssignment(lval.name):
                self.always_write('extern %s %s;\n', c_type, lval.name)

        # I think there are more than one when you do a = b = 1, which I never
        # use.
        assert len(o.lvalues) == 1, o.lvalues
        lval = o.lvalues[0]

        # GLOBAL CONSTANTS
        # Avoid Alloc<T>, since that can't be done until main().

        if self.indent == 0:
            assert isinstance(lval, NameExpr), lval
            if _SkipAssignment(lval.name):
                return

            #self.log('    GLOBAL: %s', lval.name)

            lval_type = self.types[lval]

            # Global
            #   L = [1, 2]  # type: List[int]
            if isinstance(o.rvalue, ListExpr):
                item_type = lval_type.args[0]
                item_c_type = GetCType(item_type)

                # Any constant strings will have already been written
                # TODO: Assert that every item is a constant?
                self.def_write('GLOBAL_LIST(%s, %s, %d, ', lval.name,
                               item_c_type, len(o.rvalue.items))

                self._WriteListElements(o.rvalue.items, sep=' COMMA ')

                self.def_write(');\n')
                return

            # Global
            #   D = {"foo": "bar"}  # type: Dict[str, str]
            if isinstance(o.rvalue, DictExpr):
                key_type, val_type = lval_type.args

                key_c_type = GetCType(key_type)
                val_c_type = GetCType(val_type)

                dict_expr = o.rvalue
                self.def_write('GLOBAL_DICT(%s, %s, %s, %d, ', lval.name,
                               key_c_type, val_c_type, len(dict_expr.items))

                keys = [k for k, _ in dict_expr.items]
                values = [v for _, v in dict_expr.items]

                self._WriteListElements(keys, sep=' COMMA ')
                self.def_write(', ')
                self._WriteListElements(values, sep=' COMMA ')

                self.def_write(');\n')
                return

            # We could do GcGlobal<> for ASDL classes, but Oils doesn't use them
            if isinstance(o.rvalue, CallExpr):
                self.report_error(
                    o,
                    "Can't initialize objects at the top level, only BigStr List Dict"
                )
                return

        #
        # Non-top-level
        #

        if isinstance(o.rvalue, CallExpr):
            #    d = NewDict()  # type: Dict[int, int]
            # -> auto* d = NewDict<int, int>();
            #
            # - NewDict exists in Python, it makes ordered dictionaries
            # - We translate it here because we need type inference
            #
            # I think we could get rid of NewDict in C++, and have it only in
            # Python.
            #
            # We used to have the "allocating in a constructor" rooting
            # problem, but I believe that's gone now.

            callee = o.rvalue.callee

            if callee.name == 'NewDict':
                lval_type = self.types[lval]

                # Fix for Dict[str, value]? in ASDL

                #self.log('lval type %s', lval_type)
                if (isinstance(lval_type, UnionType) and
                        len(lval_type.items) == 2 and
                        isinstance(lval_type.items[1], NoneTyp)):
                    lval_type = lval_type.items[0]

                c_type = GetCType(lval_type)
                if self.decl:
                    self.local_var_list.append((lval.name, c_type))

                assert c_type.endswith('*')

                # Hack for declaration vs. definition.  TODO: clean this up
                prefix = '' if self.current_func_node else 'auto* '

                self.def_write_ind('%s%s = Alloc<%s>();\n', prefix, lval.name,
                                   c_type[:-1])
                return

            #    src = cast(source__SourcedFile, src)
            # -> source__SourcedFile* src = static_cast<source__SourcedFile>(src)
            if callee.name == 'cast':
                assert isinstance(lval, NameExpr)
                call = o.rvalue
                type_expr = call.args[0]
                subtype_name = _GetCTypeForCast(type_expr)

                cast_kind = _GetCastKind(self.module_path, subtype_name)

                # HACK: Distinguish between UP cast and DOWN cast.
                # osh/cmd_parse.py _MakeAssignPair does an UP cast within branches.
                # _t is the base type, so that means it's an upcast.
                if (isinstance(type_expr, NameExpr) and
                        type_expr.name.endswith('_t')):
                    if self.decl:
                        self.local_var_list.append((lval.name, subtype_name))
                    self.def_write_ind('%s = %s<%s>(', lval.name, cast_kind,
                                       subtype_name)
                else:
                    self.def_write_ind('%s %s = %s<%s>(', subtype_name,
                                       lval.name, cast_kind, subtype_name)

                self.accept(call.args[1])  # variable being casted
                self.def_write(');\n')
                return

            rval_type = self.types[o.rvalue]
            if (isinstance(rval_type, Instance) and
                    rval_type.type.fullname == 'typing.Iterator'):
                # We're calling a generator. Create a temporary List<T> on the stack
                # to accumulate the results in one big batch, then wrap it in
                # ListIter<T>.
                assert len(rval_type.args) == 1, rval_type.args
                c_type = GetCType(rval_type)
                type_param = rval_type.args[0]
                inner_c_type = GetCType(type_param)
                iter_buf = ('_iter_buf_%s' % lval.name,
                            'List<%s>*' % inner_c_type)
                self.def_write_ind('List<%s> %s;\n', inner_c_type, iter_buf[0])
                self.current_stmt_node = o
                self.yield_accumulators[o] = iter_buf
                self.def_write_ind('')
                self.accept(o.rvalue)
                self.current_stmt_node = None
                self.def_write(';\n')
                self.def_write_ind('%s %s(&%s);\n', c_type, lval.name,
                                   iter_buf[0])
                return

        if isinstance(lval, NameExpr):

            lval_type = self.types[lval]
            #c_type = GetCType(lval_type, local=self.indent != 0)
            c_type = GetCType(lval_type)

            # for "hoisting" to the top of the function
            if self.current_func_node:
                self.def_write_ind('%s = ', lval.name)
                if self.decl:
                    self.local_var_list.append((lval.name, c_type))
            else:
                # globals always get a type -- they're not mutated
                self.def_write_ind('%s %s = ', c_type, lval.name)

            # Special case for list comprehensions.  Note that a variable has to
            # be on the LHS, so we can append to it.
            #
            # y = [i+1 for i in x[1:] if i]
            #   =>
            # y = []
            # for i in x[1:]:
            #   if i:
            #     y.append(i+1)
            # (but in C++)

            if isinstance(o.rvalue, ListComprehension):
                gen = o.rvalue.generator  # GeneratorExpr
                left_expr = gen.left_expr
                index_expr = gen.indices[0]
                seq = gen.sequences[0]
                cond = gen.condlists[0]

                # BUG: can't use this to filter
                # results = [x for x in results]
                if isinstance(seq, NameExpr) and seq.name == lval.name:
                    raise AssertionError(
                        "Can't use var %r in list comprehension because it would "
                        "be overwritten" % lval.name)

                # Write empty container as initialization.
                assert c_type.endswith('*'), c_type  # Hack
                self.def_write('Alloc<%s>();\n' % c_type[:-1])

                over_type = self.types[seq]

                if over_type.type.fullname == 'builtins.list':
                    c_type = GetCType(over_type)
                    assert c_type.endswith('*'), c_type
                    c_iter_type = c_type.replace('List', 'ListIter',
                                                 1)[:-1]  # remove *
                else:
                    # Example: assoc == Optional[Dict[str, str]]
                    c_iter_type = 'TODO_ASSOC'

                self.def_write_ind('for (%s it(', c_iter_type)
                self.accept(seq)
                self.def_write('); !it.Done(); it.Next()) {\n')

                item_type = over_type.args[0]  # get 'int' from 'List<int>'

                if isinstance(item_type, Instance):
                    self.def_write_ind('  %s ', GetCType(item_type))
                    # TODO(StackRoots): for ch in 'abc'
                    self.accept(index_expr)
                    self.def_write(' = it.Value();\n')

                elif isinstance(item_type, TupleType):  # for x, y in pairs
                    c_item_type = GetCType(item_type)

                    if isinstance(index_expr, TupleExpr):
                        temp_name = 'tup%d' % self.unique_id
                        self.unique_id += 1
                        self.def_write_ind('  %s %s = it.Value();\n',
                                           c_item_type, temp_name)

                        self.indent += 1

                        self._write_tuple_unpacking(temp_name,
                                                    index_expr.items,
                                                    item_type.items)

                        self.indent -= 1
                    else:
                        raise AssertionError()

                else:
                    raise AssertionError('Unexpected type %s' % item_type)

                if cond:
                    self.indent += 1
                    self.def_write_ind('if (')
                    self.accept(cond[0])  # Just the first one
                    self.def_write(') {\n')

                self.def_write_ind('  %s->append(', lval.name)
                self.accept(left_expr)
                self.def_write(');\n')

                if cond:
                    self.def_write_ind('}\n')
                    self.indent -= 1

                self.def_write_ind('}\n')
                return

            self.accept(o.rvalue)
            self.def_write(';\n')

        elif isinstance(lval, MemberExpr):
            self.def_write_ind('')
            self.accept(lval)
            self.def_write(' = ')
            self.accept(o.rvalue)
            self.def_write(';\n')

            if self.current_method_name in ('__init__', 'Reset'):
                # Collect statements that look like self.foo = 1
                # Only do this in __init__ so that a derived class mutating a field
                # from the base class doesn't cause duplicate C++ fields.  (C++
                # allows two fields of the same name!)
                #
                # HACK for WordParser: also include Reset().  We could change them
                # all up front but I kinda like this.

                if (isinstance(lval.expr, NameExpr) and
                        lval.expr.name == 'self'):
                    #log('    lval.name %s', lval.name)
                    lval_type = self.types[lval]
                    self.member_vars[lval.name] = lval_type

        elif isinstance(lval, IndexExpr):  # a[x] = 1
            # d->set(x, 1) for both List and Dict
            self.def_write_ind('')
            self.accept(lval.base)
            self.def_write('->set(')
            self.accept(lval.index)
            self.def_write(', ')
            self.accept(o.rvalue)
            self.def_write(');\n')

        elif isinstance(lval, TupleExpr):
            # An assignment to an n-tuple turns into n+1 statements.  Example:
            #
            # x, y = mytuple
            #
            # Tuple2<int, BigStr*> tup1 = mytuple
            # int x = tup1->at0()
            # BigStr* y = tup1->at1()

            rvalue_type = self.types[o.rvalue]

            # type alias upgrade for MyPy 0.780
            if isinstance(rvalue_type, TypeAliasType):
                rvalue_type = rvalue_type.alias.target

            c_type = GetCType(rvalue_type)

            is_return = (isinstance(o.rvalue, CallExpr) and
                         o.rvalue.callee.name != "next")
            if is_return:
                assert c_type.endswith('*')
                c_type = c_type[:-1]

            temp_name = 'tup%d' % self.unique_id
            self.unique_id += 1
            self.def_write_ind('%s %s = ', c_type, temp_name)

            self.accept(o.rvalue)
            self.def_write(';\n')

            self._write_tuple_unpacking(temp_name,
                                        lval.items,
                                        rvalue_type.items,
                                        is_return=is_return)

        else:
            raise AssertionError(lval)

    def _write_body(self, body):
        """Write a block without the { }."""
        for stmt in body:
            # Ignore things that look like docstrings
            if (isinstance(stmt, ExpressionStmt) and
                    isinstance(stmt.expr, StrExpr)):
                continue

            #log('-- %d', self.indent)
            self.accept(stmt)

    def visit_for_stmt(self, o: 'mypy.nodes.ForStmt') -> T:
        if 0:
            self.log('ForStmt')
            self.log('  index_type %s', o.index_type)
            self.log('  inferred_item_type %s', o.inferred_item_type)
            self.log('  inferred_iterator_type %s', o.inferred_iterator_type)

        func_name = None  # does the loop look like 'for x in func():' ?
        if (isinstance(o.expr, CallExpr) and
                isinstance(o.expr.callee, NameExpr)):
            func_name = o.expr.callee.name

        # special case: 'for i in xrange(3)'
        if func_name == 'xrange':
            index_name = o.index.name
            args = o.expr.args
            num_args = len(args)

            if num_args == 1:  # xrange(end)
                self.def_write_ind('for (int %s = 0; %s < ', index_name,
                                   index_name)
                self.accept(args[0])
                self.def_write('; ++%s) ', index_name)

            elif num_args == 2:  # xrange(being, end)
                self.def_write_ind('for (int %s = ', index_name)
                self.accept(args[0])
                self.def_write('; %s < ', index_name)
                self.accept(args[1])
                self.def_write('; ++%s) ', index_name)

            elif num_args == 3:  # xrange(being, end, step)
                # Special case to detect a constant -1.  This is a static
                # heuristic, because it could be negative dynamically.  TODO:
                # mylib.reverse_xrange() or something?
                step = args[2]
                if isinstance(step, UnaryExpr) and step.op == '-':
                    comparison_op = '>'
                else:
                    comparison_op = '<'

                self.def_write_ind('for (int %s = ', index_name)
                self.accept(args[0])
                self.def_write('; %s %s ', index_name, comparison_op)
                self.accept(args[1])
                self.def_write('; %s += ', index_name)
                self.accept(step)
                self.def_write(') ')

            else:
                raise AssertionError()

            self.accept(o.body)
            return

        reverse = False

        # for i, x in enumerate(...):
        index0_name = None
        if func_name == 'enumerate':
            assert isinstance(o.index, TupleExpr), o.index
            index0 = o.index.items[0]
            assert isinstance(index0, NameExpr), index0
            index0_name = index0.name  # generate int i = 0; ; ++i

            # type of 'x' in 'for i, x in enumerate(...)'
            item_type = o.inferred_item_type.items[1]
            index_expr = o.index.items[1]

            # enumerate(mylist) turns into iteration over mylist with variable i
            assert len(o.expr.args) == 1, o.expr.args
            iterated_over = o.expr.args[0]

        elif func_name == 'reversed':
            # NOTE: enumerate() and reversed() can't be mixed yet.  But you CAN
            # reverse iter over tuples.
            item_type = o.inferred_item_type
            index_expr = o.index

            args = o.expr.args
            assert len(args) == 1, args
            iterated_over = args[0]

            reverse = True  # use different iterate

        elif func_name == 'iteritems':
            item_type = o.inferred_item_type
            index_expr = o.index

            args = o.expr.args
            assert len(args) == 1, args
            # This should be a dict
            iterated_over = args[0]

            #log('------------ ITERITEMS OVER %s', iterated_over)

        else:
            item_type = o.inferred_item_type
            index_expr = o.index
            iterated_over = o.expr

        over_type = self.types[iterated_over]
        if isinstance(over_type, TypeAliasType):
            over_type = over_type.alias.target

        #self.log('  iterating over type %s', over_type)
        #self.log('  iterating over type %s', over_type.type.fullname)

        over_dict = False
        yield_acc = None

        if over_type.type.fullname == 'builtins.list':
            c_type = GetCType(over_type)
            assert c_type.endswith('*'), c_type
            c_iter_type = c_type.replace('List', 'ListIter',
                                         1)[:-1]  # remove *

            # ReverseListIter!
            if reverse:
                c_iter_type = 'Reverse' + c_iter_type

        elif over_type.type.fullname == 'builtins.dict':
            # Iterator
            c_type = GetCType(over_type)
            assert c_type.endswith('*'), c_type
            c_iter_type = c_type.replace('Dict', 'DictIter',
                                         1)[:-1]  # remove *

            over_dict = True

            assert not reverse

        elif over_type.type.fullname == 'builtins.str':
            c_iter_type = 'StrIter'
            assert not reverse  # can't reverse iterate over string yet

        elif over_type.type.fullname == 'typing.Iterator':
            # We're iterating over a generator. Create a temporary List<T> on the stack
            # to accumulate the results in one big batch.
            c_iter_type = GetCType(over_type)
            assert len(over_type.args) == 1, over_type.args
            inner_c_type = GetCType(over_type.args[0])
            yield_acc = ('_for_yield_acc%d' % self.unique_id,
                         'List<%s>*' % inner_c_type)
            self.unique_id += 1
            self.def_write_ind('List<%s> %s;\n', inner_c_type, yield_acc[0])
            self.def_write_ind('')
            self.yield_accumulators[o] = yield_acc
            self.current_stmt_node = o
            self.accept(iterated_over)
            self.current_stmt_node = None
            self.def_write(';\n')

        else:  # assume it's like d.iteritems()?  Iterator type
            assert False, over_type

        if index0_name:
            # can't initialize two things in a for loop, so do it on a separate line
            if self.decl:
                self.local_var_list.append((index0_name, 'int'))
            self.def_write_ind('%s = 0;\n', index0_name)
            index_update = ', ++%s' % index0_name
        else:
            index_update = ''

        self.def_write_ind('for (%s it(', c_iter_type)
        if yield_acc:
            self.def_write('&%s', yield_acc[0])
        else:
            self.accept(iterated_over)  # the thing being iterated over
        self.def_write('); !it.Done(); it.Next()%s) {\n', index_update)

        # for x in it: ...
        # for i, x in enumerate(pairs): ...

        if isinstance(item_type, Instance) or index0_name:
            c_item_type = GetCType(item_type)
            self.def_write_ind('  %s ', c_item_type)
            self.accept(index_expr)
            if over_dict:
                self.def_write(' = it.Key();\n')
            else:
                self.def_write(' = it.Value();\n')

            # Register loop variable as a stack root.
            # Note we have mylib.Collect() in CommandEvaluator::_Execute(), and
            # it's called in a loop by _ExecuteList().  Although the 'child'
            # variable is already live by other means.
            # TODO: Test how much this affects performance.
            if CTypeIsManaged(c_item_type):
                self.def_write_ind('  StackRoot _for(&')
                self.accept(index_expr)
                self.def_write_ind(');\n')

        elif isinstance(item_type, TupleType):  # for x, y in pairs
            if over_dict:
                assert isinstance(o.index, TupleExpr), o.index
                index_items = o.index.items
                assert len(index_items) == 2, index_items
                assert len(item_type.items) == 2, item_type.items

                key_type = GetCType(item_type.items[0])
                val_type = GetCType(item_type.items[1])

                #log('** %s key_type %s', item_type.items[0], key_type)
                #log('** %s val_type %s', item_type.items[1], val_type)

                # TODO(StackRoots): k, v
                self.def_write_ind('  %s %s = it.Key();\n', key_type,
                                   index_items[0].name)
                self.def_write_ind('  %s %s = it.Value();\n', val_type,
                                   index_items[1].name)

            else:
                # Example:
                # for (ListIter it(mylist); !it.Done(); it.Next()) {
                #   Tuple2<int, BigStr*> tup1 = it.Value();
                #   int i = tup1->at0();
                #   BigStr* s = tup1->at1();
                #   log("%d %s", i, s);
                # }

                c_item_type = GetCType(item_type)

                if isinstance(o.index, TupleExpr):
                    # TODO(StackRoots)
                    temp_name = 'tup%d' % self.unique_id
                    self.unique_id += 1
                    self.def_write_ind('  %s %s = it.Value();\n', c_item_type,
                                       temp_name)

                    self.indent += 1

                    self._write_tuple_unpacking(temp_name, o.index.items,
                                                item_type.items)

                    self.indent -= 1
                else:
                    self.def_write_ind('  %s %s = it.Value();\n', c_item_type,
                                       o.index.name)
                    #self.def_write_ind('  StackRoots _for(&%s)\n;', o.index.name)

        else:
            raise AssertionError('Unexpected type %s' % item_type)

        # Copy of visit_block, without opening {
        self.indent += 1
        block = o.body
        self._write_body(block.body)
        self.indent -= 1
        self.def_write_ind('}\n')

        if o.else_body:
            raise AssertionError("can't translate for-else")

    def _write_cases(self, if_node):
        """
        The MyPy AST has a recursive structure for if-elif-elif rather than a
        flat one.  It's a bit confusing.
        """
        assert isinstance(if_node, IfStmt), if_node
        assert len(if_node.expr) == 1, if_node.expr
        assert len(if_node.body) == 1, if_node.body

        expr = if_node.expr[0]
        body = if_node.body[0]

        # case 1:
        # case 2:
        # case 3: {
        #   print('body')
        # }
        #   break;  // this indent is annoying but hard to get rid of
        assert isinstance(expr, CallExpr), expr
        for i, arg in enumerate(expr.args):
            if i != 0:
                self.def_write('\n')
            self.def_write_ind('case ')
            self.accept(arg)
            self.def_write(': ')

        self.accept(body)
        self.def_write_ind('  break;\n')

        if if_node.else_body:
            first_of_block = if_node.else_body.body[0]
            # BUG: this is meant for 'elif' only.  But it also triggers for
            #
            # else:
            #   if 0:

            if isinstance(first_of_block, IfStmt):
                self._write_cases(first_of_block)
            else:
                # end the recursion
                self.def_write_ind('default: ')
                self.accept(if_node.else_body)  # the whole block
                # no break here

    def _write_switch(self, expr, o):
        """Write a switch statement over integers."""
        assert len(expr.args) == 1, expr.args

        self.def_write_ind('switch (')
        self.accept(expr.args[0])
        self.def_write(') {\n')

        assert len(o.body.body) == 1, o.body.body
        if_node = o.body.body[0]
        assert isinstance(if_node, IfStmt), if_node

        self.indent += 1
        self._write_cases(if_node)

        self.indent -= 1
        self.def_write_ind('}\n')

    def _write_str_switch(self, expr, o):
        """Write a switch statement over strings."""
        assert len(expr.args) == 1, expr.args

        self.def_write_ind('switch (')
        self.accept(expr.args[0])
        self.def_write(') {\n')

        assert len(o.body.body) == 1, o.body.body
        if_node = o.body.body[0]
        assert isinstance(if_node, IfStmt), if_node

        self.indent += 1
        self._write_cases(if_node)

        self.indent -= 1
        self.def_write_ind('}\n')

    def _write_tag_switch(self, expr, o):
        """Write a switch statement over ASDL types."""
        assert len(expr.args) == 1, expr.args

        self.def_write_ind('switch (')
        self.accept(expr.args[0])
        self.def_write('->tag()) {\n')

        assert len(o.body.body) == 1, o.body.body
        if_node = o.body.body[0]
        assert isinstance(if_node, IfStmt), if_node

        self.indent += 1
        self._write_cases(if_node)

        self.indent -= 1
        self.def_write_ind('}\n')

    def visit_with_stmt(self, o: 'mypy.nodes.WithStmt') -> T:
        """
        Translate only blocks of this form:

        with switch(x) as case:
          if case(0):
            print('zero')
          elif case(1, 2, 3):
            print('low')
          else:
            print('other')

        switch(x) {
          case 0:
            # TODO: need casting here
            print('zero')
            break;
          case 1:
          case 2:
          case 3:
            print('low')
            break;
          default:
            print('other')
            break;
        }

        Or:

        with ctx_Bar(bar, x, y):
          x()

        {
          ctx_Bar(bar, x, y)
          x();
        }
        """
        #log('WITH')
        #log('expr %s', o.expr)
        #log('target %s', o.target)

        assert len(o.expr) == 1, o.expr
        expr = o.expr[0]
        assert isinstance(expr, CallExpr), expr

        callee_name = expr.callee.name
        if callee_name == 'switch':
            self._write_switch(expr, o)
        elif callee_name == 'str_switch':
            self._write_str_switch(expr, o)
        elif callee_name == 'tagswitch':
            self._write_tag_switch(expr, o)
        else:
            assert isinstance(expr, CallExpr), expr
            self.def_write_ind('{  // with\n')
            self.indent += 1

            self.def_write_ind('')
            self.accept(expr.callee)

            # FIX: Use braced initialization to avoid most-vexing parse when
            # there are 0 args!
            self.def_write(' ctx{')
            for i, arg in enumerate(expr.args):
                if i != 0:
                    self.def_write(', ')
                self.accept(arg)
            self.def_write('};\n\n')

            #self.def_write_ind('')
            self._write_body(o.body.body)

            self.indent -= 1
            self.def_write_ind('}\n')

    def visit_del_stmt(self, o: 'mypy.nodes.DelStmt') -> T:

        d = o.expr
        if isinstance(d, IndexExpr):
            self.def_write_ind('')
            self.accept(d.base)

            if isinstance(d.index, SliceExpr):
                # del mylist[:] -> mylist->clear()

                sl = d.index
                assert sl.begin_index is None, sl
                assert sl.end_index is None, sl
                self.def_write('->clear()')
            else:
                # del mydict[mykey] raises KeyError, which we don't want
                raise AssertionError(
                    'Use mylib.maybe_remove(d, key) instead of del d[key]')

            self.def_write(';\n')

    def _WriteFuncParams(self,
                         arg_types,
                         arguments,
                         update_locals=False,
                         write_defaults=False):
        """Write params for function/method signatures.

        Optionally mutate self.local_vars, and optionally write default arguments.
        """
        if write_defaults:
            # Check if default args are valid first

            num_defaults = 0
            for arg in arguments:
                if arg.initializer:
                    t = self.types[arg.initializer]

                    valid = False
                    if isinstance(t, NoneType):
                        valid = True
                    if isinstance(t, Instance):
                        # Allowing strings since they're immutable, e.g.
                        # prefix='' seems OK
                        if t.type.fullname in ('builtins.bool', 'builtins.int',
                                               'builtins.float',
                                               'builtins.str'):
                            valid = True

                        # ASDL enums lex_mode_t, scope_t, ...
                        if t.type.fullname.endswith('_t'):
                            valid = True

                        # Hack for loc__Missing.  Should detect the general case.
                        if t.type.fullname.endswith('loc__Missing'):
                            valid = True

                    if not valid:
                        self.report_error(
                            arg,
                            'Invalid default arg %r of type %s (not None, bool, int, float, ASDL enum)'
                            % (arg.initializer, t))
                        return

                    num_defaults += 1

            if num_defaults > 1:
                name = '[TODO]'
                #if class_name:
                #  name = '%s::%s' % (class_name, func_name)
                #else:
                #  name = func_name

                # Report on first arg
                self.report_error(
                    arg, '%s has %d default arguments.  Only 1 is allowed' %
                    (name, num_defaults))
                return

        first = True  # first NOT including self
        for arg_type, arg in zip(arg_types, arguments):
            if not first:
                self.always_write(', ')

            # TODO: Turn this on.  Having stdlib problems, e.g.
            # examples/cartesian.
            c_type = GetCType(arg_type, param=False)

            arg_name = arg.variable.name

            # C++ has implicit 'this'
            if arg_name == 'self':
                continue

            self.always_write('%s %s', c_type, arg_name)
            if write_defaults and arg.initializer:
                self.always_write(' = ')

                # Silly mechanism to activate self.def_write()
                self.writing_default_arg = True
                self.accept(arg.initializer)
                self.writing_default_arg = False

            first = False

            # Params are locals.  There are 4 callers to _WriteFuncParams and we
            # only do it in one place.  TODO: Check if locals are used in
            # __init__ after allocation.
            if update_locals:
                self.local_var_list.append((arg_name, c_type))

            # We can't use __str__ on these Argument objects?  That seems like an
            # oversight
            #self.log('%r', arg)

            if 0:
                self.log('Argument %s', arg.variable)
                self.log('  type_annotation %s', arg.type_annotation)
                # I think these are for default values
                self.log('  initializer %s', arg.initializer)
                self.log('  kind %s', arg.kind)

        # Will be set if we're declaring or defining a function that returns
        # Iterator[T].
        if self.current_func_node in self.yield_accumulators:
            if not first:
                self.always_write(', ')

            arg_name, c_type = self.yield_accumulators[self.current_func_node]
            self.always_write('%s %s', c_type, arg_name)

    def visit_func_def(self, o: 'mypy.nodes.FuncDef') -> T:
        if o.name == '__repr__':  # Don't translate
            return

        # No function prototypes when forward declaring.
        if self.forward_decl:
            self.virtual.OnMethod(self.current_class_name, o.name)
            return

        func_name = o.name

        virtual = ''
        if self.decl:
            self.local_var_list = []  # Make a new instance to collect from
            self.local_vars[o] = self.local_var_list

            if self.virtual.IsVirtual(self.current_class_name, o.name):
                virtual = 'virtual '

        if not self.decl and self.current_class_name:
            # definition looks like
            # void Class::method(...);
            func_name = '%s::%s' % (self.current_class_name, o.name)
        else:
            # declaration inside class { }
            func_name = o.name

        self.def_write('\n')

        c_ret_type, _, c_iter_list_type = GetCReturnType(o.type.ret_type)
        if c_iter_list_type is not None:
            # The function is a generator. Add an output param that references an
            # accumulator for the results.
            self.yield_accumulators[o] = ('_out_yield_acc', c_iter_list_type)

        # Avoid ++ warnings by prepending [[noreturn]]
        noreturn = ''
        if func_name in ('e_die', 'e_die_status', 'e_strict', 'e_usage',
                         'p_die'):
            noreturn = '[[noreturn]] '

        self.always_write_ind('%s%s%s %s(', noreturn, virtual, c_ret_type,
                              func_name)

        self.current_func_node = o
        self._WriteFuncParams(
            o.type.arg_types,
            o.arguments,
            update_locals=True,
            # write default values in the declaration only
            write_defaults=self.decl)

        if self.decl:
            self.always_write(');\n')
            self.accept(
                o.body)  # Collect member_vars, but don't write anything

            self.current_func_node = None
            return

        self.def_write(') ')

        # Write local vars we collected in the 'decl' phase
        if not self.forward_decl and not self.decl:
            arg_names = [arg.variable.name for arg in o.arguments]
            #log('arg_names %s', arg_names)
            #log('local_vars %s', self.local_vars[o])
            self.prepend_to_block = [
                (lval_name, c_type, lval_name in arg_names)
                for (lval_name, c_type) in self.local_vars[o]
            ]

        self.accept(o.body)
        self.current_func_node = None

    def visit_overloaded_func_def(self,
                                  o: 'mypy.nodes.OverloadedFuncDef') -> T:
        pass

    def visit_class_def(self, o: 'mypy.nodes.ClassDef') -> T:
        #log('  CLASS %s', o.name)

        base_class_name = None  # single inheritance only
        for b in o.base_type_exprs:
            if isinstance(b, NameExpr):
                # TODO: inherit from std::exception?
                if b.name != 'object' and b.name != 'Exception':
                    base_class_name = b.name
            elif isinstance(b, MemberExpr):  # vm._Executor -> vm::_Executor
                assert isinstance(b.expr, NameExpr), b
                base_class_name = '%s::%s' % (b.expr.name, b.name)

        # Forward declare types because they may be used in prototypes
        if self.forward_decl:
            self.always_write_ind('class %s;\n', o.name)
            if base_class_name:
                self.virtual.OnSubclass(base_class_name, o.name)
            # Visit class body so we get method declarations
            self.current_class_name = o.name
            self._write_body(o.defs.body)
            self.current_class_name = None
            return

        if self.decl:
            self.member_vars.clear()  # make a new list

            self.always_write_ind('class %s', o.name)  # block after this

            # e.g. class TextOutput : public ColorOutput
            if base_class_name:
                self.always_write(' : public %s', base_class_name)

            self.always_write(' {\n')
            self.always_write_ind(' public:\n')

            block = o.defs

            self.indent += 1
            self.current_class_name = o.name
            for stmt in block.body:

                # Ignore things that look like docstrings
                if (isinstance(stmt, ExpressionStmt) and
                        isinstance(stmt.expr, StrExpr)):
                    continue

                # Constructor is named after class
                if isinstance(stmt, FuncDef):
                    method_name = stmt.name
                    if method_name == '__init__':
                        self.always_write_ind('%s(', o.name)
                        self._WriteFuncParams(stmt.type.arg_types,
                                              stmt.arguments,
                                              write_defaults=True)
                        self.always_write(');\n')

                        # Visit for member vars
                        self.current_method_name = method_name
                        self.accept(stmt.body)
                        self.current_method_name = None
                        continue

                    if method_name == '__enter__':
                        continue

                    if method_name == '__exit__':
                        # Turn it into a destructor with NO ARGS
                        self.always_write_ind('~%s();\n', o.name)
                        continue

                    if method_name == '__repr__':
                        # skip during declaration, just like visit_func_def does during definition
                        continue

                    # Any other function: Visit for member vars
                    self.current_method_name = method_name
                    self.accept(stmt)
                    self.current_method_name = None
                    continue

                # TODO: Remove this?  Everything under a class is a method?
                self.accept(stmt)

            # List of field mask expressions
            mask_bits = []
            if self.virtual.CanReorderFields(o.name):
                # No inheritance, so we are free to REORDER member vars, putting
                # pointers at the front.

                pointer_members = []
                non_pointer_members = []

                for name in self.member_vars:
                    c_type = GetCType(self.member_vars[name])
                    if CTypeIsManaged(c_type):
                        pointer_members.append(name)
                    else:
                        non_pointer_members.append(name)

                # So we declare them in the right order
                sorted_member_names = pointer_members + non_pointer_members

                self.field_gc[o] = ('HeapTag::Scanned', len(pointer_members))
            else:
                # Has inheritance

                # The field mask of a derived class is unioned with its base's
                # field mask.
                if base_class_name:
                    mask_bits.append('%s::field_mask()' % base_class_name)

                for name in sorted(self.member_vars):
                    c_type = GetCType(self.member_vars[name])
                    if CTypeIsManaged(c_type):
                        mask_bits.append('maskbit(offsetof(%s, %s))' %
                                         (o.name, name))

                # A base class with no fields has kZeroMask.
                if not base_class_name and not mask_bits:
                    mask_bits.append('kZeroMask')

                sorted_member_names = sorted(self.member_vars)

                self.field_gc[o] = ('HeapTag::FixedSize', 'field_mask()')

            # Write member variables

            #log('MEMBERS for %s: %s', o.name, list(self.member_vars.keys()))
            if self.member_vars:
                if base_class_name:
                    self.always_write('\n')  # separate from functions

                for name in sorted_member_names:
                    c_type = GetCType(self.member_vars[name])
                    self.always_write_ind('%s %s;\n', c_type, name)

            self.current_class_name = None

            if mask_bits:
                self.always_write_ind('\n')
                self.always_write_ind(
                    'static constexpr uint32_t field_mask() {\n')
                self.always_write_ind('  return ')
                for i, b in enumerate(mask_bits):
                    if i != 0:
                        self.always_write('\n')
                        self.always_write_ind('       | ')
                    self.always_write(b)
                self.always_write(';\n')
                self.always_write_ind('}\n')

            obj_tag, obj_arg = self.field_gc[o]
            if obj_tag == 'HeapTag::FixedSize':
                obj_mask = obj_arg
                obj_header = 'ObjHeader::ClassFixed(%s, sizeof(%s))' % (
                    obj_mask, o.name)
            elif obj_tag == 'HeapTag::Scanned':
                num_pointers = obj_arg
                obj_header = 'ObjHeader::ClassScanned(%s, sizeof(%s))' % (
                    num_pointers, o.name)
            else:
                raise AssertionError(o.name)

            self.always_write('\n')
            self.always_write_ind(
                'static constexpr ObjHeader obj_header() {\n')
            self.always_write_ind('  return %s;\n' % obj_header)
            self.always_write_ind('}\n')

            self.always_write('\n')
            self.always_write_ind('DISALLOW_COPY_AND_ASSIGN(%s)\n', o.name)
            self.indent -= 1
            self.always_write_ind('};\n')
            self.always_write('\n')

            return

        self.current_class_name = o.name

        #
        # Now we're visiting for definitions (not declarations).
        #
        block = o.defs
        for stmt in block.body:
            if isinstance(stmt, FuncDef):
                # Collect __init__ calls within __init__, and turn them into
                # initializer lists.
                if stmt.name == '__init__':
                    self.def_write('\n')
                    self.def_write('%s::%s(', o.name, o.name)
                    self._WriteFuncParams(stmt.type.arg_types, stmt.arguments)
                    self.def_write(')')

                    # Check for Base.__init__(self, ...) and move that to the initializer list.

                    first_index = 0

                    # Skip docstring
                    maybe_skip_stmt = stmt.body.body[0]
                    if (isinstance(maybe_skip_stmt, ExpressionStmt) and
                            isinstance(maybe_skip_stmt.expr, StrExpr)):
                        first_index += 1

                    first_stmt = stmt.body.body[first_index]
                    if (isinstance(first_stmt, ExpressionStmt) and
                            isinstance(first_stmt.expr, CallExpr)):
                        expr = first_stmt.expr
                        #log('expr %s', expr)
                        callee = first_stmt.expr.callee

                        # TextOutput() : ColorOutput(f), ... {
                        if (isinstance(callee, MemberExpr) and
                                callee.name == '__init__'):
                            base_constructor_args = expr.args
                            #log('ARGS %s', base_constructor_args)
                            self.def_write(' : %s(', base_class_name)
                            for i, arg in enumerate(base_constructor_args):
                                if i == 0:
                                    continue  # Skip 'this'
                                if i != 1:
                                    self.def_write(', ')
                                self.accept(arg)
                            self.def_write(')')

                            first_index += 1

                    self.def_write(' {\n')

                    # Debug Tag!
                    # self.def_write('  type_tag_ = kMycppDebugType;\n')

                    # Now visit the rest of the statements
                    self.indent += 1
                    for node in stmt.body.body[first_index:]:
                        self.accept(node)
                    self.indent -= 1
                    self.def_write('}\n')

                    continue  # wrote FuncDef for constructor

                if stmt.name == '__enter__':
                    continue

                if stmt.name == '__exit__':
                    self.always_write('\n')
                    self.always_write_ind('%s::~%s()', o.name, o.name)
                    self.accept(stmt.body)
                    continue

                self.accept(stmt)

        self.current_class_name = None  # Stop prefixing functions with class

    def visit_global_decl(self, o: 'mypy.nodes.GlobalDecl') -> T:
        pass

    def visit_nonlocal_decl(self, o: 'mypy.nodes.NonlocalDecl') -> T:
        pass

    def visit_decorator(self, o: 'mypy.nodes.Decorator') -> T:
        pass

    def visit_var(self, o: 'mypy.nodes.Var') -> T:
        pass

    # Module structure

    def visit_import(self, o: 'mypy.nodes.Import') -> T:
        for name, as_name in o.ids:
            if as_name is not None:
                # import time as time_
                self.imported_names.add(as_name)
            else:
                # import libc
                self.imported_names.add(name)

    def visit_import_from(self, o: 'mypy.nodes.ImportFrom') -> T:
        """
        Write C++ namespace aliases and 'using' for imports.
        We need them in the 'decl' phase for default arguments like
        runtime_asdl::scope_e -> scope_e
        """
        # For MemberExpr . -> module::func() or this->field.  Also needed in
        # the decl phase for default arg values.
        for name, alias in o.names:
            if alias:
                self.imported_names.add(alias)
            else:
                self.imported_names.add(name)

        if o.id in ('__future__', 'typing'):
            return  # do nothing

        #self.log('    %s ImportFrom id: %s', self.decl, o.id)

        for name, alias in o.names:
            #self.log('ImportFrom id: %s name: %s alias: %s', o.id, name, alias)

            if name == 'log':  # varargs translation
                continue
            if name == 'stderr_line':  # TODO: remove this
                continue

            if o.id == 'mycpp.mylib':
                # These mylib functions are translated in a special way
                if name in ('switch', 'tagswitch', 'iteritems', 'NewDict'):
                    continue
                # STDIN_FILENO is #included
                if name == 'STDIN_FILENO':
                    continue

            # A heuristic that works for the Oil import style.
            if '.' in o.id:
                # from mycpp.mylib import log => using mylib::log
                translate_import = True
            else:
                # from core import util => NOT translated
                # We just rely on 'util' being defined.
                translate_import = False

            if translate_import:
                dotted_parts = o.id.split('.')
                last_dotted = dotted_parts[-1]

                # Omit these:
                #   from _gen.ysh import grammar_nt
                if last_dotted == 'ysh':
                    return
                #   from _devbuild.gen import syntax_asdl
                if last_dotted == 'gen':
                    return

                # Problem:
                # - The decl stage has to return yaks_asdl::mod_def, so imports should go there
                # - But if you change this to decl_write() instead of
                #   def_write(), you end up 'using error::e_usage' in say
                #   'assign_osh', and it hasn't been defined yet.

                if alias:
                    # using runtime_asdl::emit_e = EMIT;
                    self.def_write_ind('using %s = %s::%s;\n', alias,
                                       last_dotted, name)
                else:
                    #    from _devbuild.gen.id_kind_asdl import Id
                    # -> using id_kind_asdl::Id.

                    using_str = 'using %s::%s;\n' % (last_dotted, name)
                    self.def_write_ind(using_str)

                    # Fully qualified:
                    # self.def_write_ind('using %s::%s;\n', '::'.join(dotted_parts), name)

                    # Hack for default args.  Without this limitation, we write
                    # 'using' of names that aren't declared yet.
                    # suffix_op is needed for string_ops.py, for some reason
                    if (name in ('Id', 'scope_e', 'lex_mode_e', 'suffix_op',
                                 'sh_lvalue', 'part_value', 'loc', 'word',
                                 'word_part', 'cmd_value', 'hnode')):
                        self.decl_write(using_str)

            else:
                # If we're importing a module without an alias, we don't need to do
                # anything.  'namespace cmd_eval' is already defined.
                if not alias:
                    return

                #    from asdl import format as fmt
                # -> namespace fmt = format;
                self.def_write_ind('namespace %s = %s;\n', alias, name)

    def visit_import_all(self, o: 'mypy.nodes.ImportAll') -> T:
        pass

    # Statements

    def visit_block(self, block: 'mypy.nodes.Block') -> T:
        self.def_write('{\n')  # not indented to use same line as while/if

        self.indent += 1

        if self.prepend_to_block:
            # TODO: put the pointers first, and then register a single
            # StackRoots record.
            done = set()
            for lval_name, c_type, is_param in self.prepend_to_block:
                if not is_param and lval_name not in done:
                    if util.SMALL_STR and c_type == 'Str':
                        self.def_write_ind('%s %s(nullptr);\n', c_type,
                                           lval_name)
                    else:
                        rhs = ' = nullptr' if CTypeIsManaged(c_type) else ''
                        self.def_write_ind('%s %s%s;\n', c_type, lval_name,
                                           rhs)

                    done.add(lval_name)

            # Figure out if we have any roots to write with StackRoots
            roots = []  # keep it sorted
            for lval_name, c_type, is_param in self.prepend_to_block:
                #self.log('%s %s %s', lval_name, c_type, is_param)
                if lval_name not in roots and CTypeIsManaged(c_type):
                    roots.append(lval_name)
            #self.log('roots %s', roots)

            if len(roots):
                if (self.stack_roots_warn and
                        len(roots) > self.stack_roots_warn):
                    log('WARNING: %s::%s() has %d stack roots. Consider refactoring this function.'
                        % (self.current_class_name or
                           '', self.current_func_node.name, len(roots)))

                for i, r in enumerate(roots):
                    self.def_write_ind('StackRoot _root%d(&%s);\n' % (i, r))

                self.def_write('\n')

            self.prepend_to_block = None

        self._write_body(block.body)

        self.indent -= 1
        self.def_write_ind('}\n')

    def visit_expression_stmt(self, o: 'mypy.nodes.ExpressionStmt') -> T:
        # TODO: Avoid writing docstrings.
        # If it's just a string, then we don't need it.

        self.def_write_ind('')
        self.accept(o.expr)
        self.def_write(';\n')

    def visit_operator_assignment_stmt(
            self, o: 'mypy.nodes.OperatorAssignmentStmt') -> T:
        self.def_write_ind('')
        self.accept(o.lvalue)
        self.def_write(' %s= ', o.op)  # + to +=
        self.accept(o.rvalue)
        self.def_write(';\n')

    def visit_while_stmt(self, o: 'mypy.nodes.WhileStmt') -> T:
        self.def_write_ind('while (')
        self.accept(o.expr)
        self.def_write(') ')
        self.accept(o.body)

    def visit_return_stmt(self, o: 'mypy.nodes.ReturnStmt') -> T:
        # Examples:
        # return
        # return None
        # return my_int + 3;
        self.def_write_ind('return ')
        if o.expr:
            if not (isinstance(o.expr, NameExpr) and o.expr.name == 'None'):

                # Note: the type of the return expression (self.types[o.expr])
                # and the return type of the FUNCTION are different.  Use the
                # latter.
                ret_type = self.current_func_node.type.ret_type

                c_ret_type, returning_tuple, _ = GetCReturnType(ret_type)

                # return '', None  # tuple literal
                #   but NOT
                # return tuple_func()
                if returning_tuple and isinstance(o.expr, TupleExpr):
                    self.def_write('%s(' % c_ret_type)
                    for i, item in enumerate(o.expr.items):
                        if i != 0:
                            self.def_write(', ')
                        self.accept(item)
                    self.def_write(');\n')
                    return

            # Not returning tuple
            self.accept(o.expr)

        self.def_write(';\n')

    def visit_assert_stmt(self, o: 'mypy.nodes.AssertStmt') -> T:
        pass

    def visit_if_stmt(self, o: 'mypy.nodes.IfStmt') -> T:
        # Not sure why this wouldn't be true
        assert len(o.expr) == 1, o.expr

        cond = o.expr[0]

        if not _CheckCondition(cond, self.types):
            self.report_error(
                o,
                "Use explicit len(obj) or 'obj is not None' for mystr, mylist, mydict"
            )
            return

        # Omit anything that looks like if __name__ == ...
        if (isinstance(cond, ComparisonExpr) and
                isinstance(cond.operands[0], NameExpr) and
                cond.operands[0].name == '__name__'):
            return

        # Omit if 0:
        if isinstance(cond, IntExpr) and cond.value == 0:
            # But write else: body
            # Note: this would be invalid at the top level!
            if o.else_body:
                self.accept(o.else_body)
            return

        # Omit if TYPE_CHECKING blocks.  They contain type expressions that
        # don't type check!
        if isinstance(cond, NameExpr) and cond.name == 'TYPE_CHECKING':
            return
        # mylib.CPP
        if isinstance(cond, MemberExpr) and cond.name == 'CPP':
            # just take the if block
            self.def_write_ind('// if MYCPP\n')
            self.def_write_ind('')
            for node in o.body:
                self.accept(node)
            self.def_write_ind('// endif MYCPP\n')
            return
        # mylib.PYTHON
        if isinstance(cond, MemberExpr) and cond.name == 'PYTHON':
            if o.else_body:
                self.def_write_ind('// if not PYTHON\n')
                self.def_write_ind('')
                self.accept(o.else_body)
                self.def_write_ind('// endif MYCPP\n')
            return

        self.def_write_ind('if (')
        for e in o.expr:
            self.accept(e)
        self.def_write(') ')

        for node in o.body:
            self.accept(node)

        if o.else_body:
            self.def_write_ind('else ')
            self.accept(o.else_body)

    def visit_break_stmt(self, o: 'mypy.nodes.BreakStmt') -> T:
        self.def_write_ind('break;\n')

    def visit_continue_stmt(self, o: 'mypy.nodes.ContinueStmt') -> T:
        self.def_write_ind('continue;\n')

    def visit_pass_stmt(self, o: 'mypy.nodes.PassStmt') -> T:
        self.def_write_ind(';  // pass\n')

    def visit_raise_stmt(self, o: 'mypy.nodes.RaiseStmt') -> T:
        # C++ compiler is aware of assert(0) for unreachable code
        if o.expr and isinstance(o.expr, CallExpr):
            if o.expr.callee.name == 'AssertionError':
                self.def_write_ind('assert(0);  // AssertionError\n')
                return
            if o.expr.callee.name == 'NotImplementedError':
                self.def_write_ind(
                    'FAIL(kNotImplemented);  // Python NotImplementedError\n')
                return

        self.def_write_ind('throw ')
        # it could be raise -> throw ; .  OSH uses that.
        if o.expr:
            self.accept(o.expr)
        self.def_write(';\n')

    def visit_try_stmt(self, o: 'mypy.nodes.TryStmt') -> T:
        self.def_write_ind('try ')
        self.accept(o.body)
        caught = False

        for t, v, handler in zip(o.types, o.vars, o.handlers):
            c_type = None

            if isinstance(t, NameExpr):
                if t.name in ('IOError', 'OSError'):
                    self.report_error(
                        handler,
                        'Use except (IOError, OSError) rather than catching just one'
                    )
                c_type = '%s*' % t.name

            elif isinstance(t, MemberExpr):
                # Heuristic
                c_type = '%s::%s*' % (t.expr.name, t.name)

            elif isinstance(t, TupleExpr):
                if len(t.items) == 2:
                    e1 = t.items[0]
                    e2 = t.items[1]
                    if isinstance(e1, NameExpr) and isinstance(e2, NameExpr):
                        names = [e1.name, e2.name]
                        names.sort()
                        if names == ['IOError', 'OSError']:
                            c_type = 'IOError_OSError*'  # Base class in mylib

            else:
                raise AssertionError()

            if c_type is None:
                c_type = 'INVALID_TRY_EXCEPT'  # Causes compile error

            if v:
                self.def_write_ind('catch (%s %s) ', c_type, v.name)
            else:
                self.def_write_ind('catch (%s) ', c_type)
            self.accept(handler)

            caught = True

        # DUMMY to prevent compile errors
        # TODO: Remove this
        if not caught:
            self.def_write_ind('catch (std::exception const&) { }\n')

        if o.else_body:
            self.report_error(o, 'try/else not supported')

        if o.finally_body:
            self.report_error(o, 'try/finally not supported')

    def visit_print_stmt(self, o: 'mypy.nodes.PrintStmt') -> T:
        self.report_error(
            o,
            'File should start with "from __future__ import print_function"')

    def visit_exec_stmt(self, o: 'mypy.nodes.ExecStmt') -> T:
        pass
