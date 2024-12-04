"""
cppgen_pass.py - AST pass that prints C++ code
"""
import itertools
import json  # for "C escaping"

from typing import Union, Optional, Dict

import mypy
from mycpp import visitor
from mypy.types import (Type, AnyType, NoneTyp, TupleType, Instance,
                        Overloaded, CallableType, UnionType, UninhabitedType,
                        PartialType, TypeAliasType)
from mypy.nodes import (Expression, Statement, NameExpr, IndexExpr, MemberExpr,
                        TupleExpr, ExpressionStmt, IfStmt, StrExpr, SliceExpr,
                        FuncDef, UnaryExpr, OpExpr, CallExpr, ListExpr,
                        DictExpr, ClassDef, ForStmt, AssignmentStmt)

from mycpp import format_strings
from mycpp.util import log, join_name, split_py_name, IsStr
from mycpp import pass_state
from mycpp import util

from typing import Tuple, List, Any, TYPE_CHECKING
if TYPE_CHECKING:
    from mycpp import const_pass
    from mycpp import ir_pass


def _IsContextManager(class_name: util.SymbolPath) -> bool:
    return class_name[-1].startswith('ctx_')


def _GetCTypeForCast(type_expr: Expression) -> str:
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


def _GetCastKind(module_path: str, cast_to_type: str) -> str:
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


def _ContainsFunc(t: Type) -> Optional[str]:
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

        contains_func = _ContainsFunc(t.items[0])

    return contains_func  # None checked later


def _EqualsFunc(left_type: Type) -> Optional[str]:
    if IsStr(left_type):
        return 'str_equals'

    if (isinstance(left_type, UnionType) and len(left_type.items) == 2 and
            IsStr(left_type.items[0]) and
            isinstance(left_type.items[1], NoneTyp)):
        return 'maybe_str_equals'

    return None


_EXPLICIT = ('builtins.str', 'builtins.list', 'builtins.dict')


def _CheckCondition(node: Expression, types: Dict[Expression, Type]) -> bool:
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
        return (_CheckCondition(node.left, types) and
                _CheckCondition(node.right, types))

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


def CTypeIsManaged(c_type: str) -> bool:
    """For rooting and field masks."""
    assert c_type != 'void'

    if util.SMALL_STR:
        if c_type == 'Str':
            return True

    # int, double, bool, scope_t enums, etc. are not managed
    return c_type.endswith('*')


def GetCType(t: Type) -> str:
    """Recursively translate MyPy type to C++ type."""
    is_pointer = False

    if isinstance(t, UninhabitedType):
        # UninhabitedType is used by def e_usage() -> NoReturn
        # TODO: we could add [[noreturn]] here!
        c_type = 'void'

    elif isinstance(t, PartialType):
        # I removed the last instance of this!  It was dead code in comp_ui.py.
        raise AssertionError()
        #c_type = 'void'
        #is_pointer = True

    elif isinstance(t,
                    NoneTyp):  # e.g. a function that doesn't return anything
        return 'void'

    elif isinstance(t, AnyType):
        # 'any' in ASDL becomes void*
        # It's useful for value::BuiltinFunc(void* f) which is a vm::_Callable*
        c_type = 'void'
        is_pointer = True

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

        elif 'BigInt' in type_name:
            # also spelled mycpp.mylib.BigInt

            c_type = 'mops::BigInt'
            # Not a pointer!

        elif type_name == 'typing.IO':
            c_type = 'mylib::File'
            is_pointer = True

        # Parameterized types: List, Dict, Iterator
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

        elif type_name == 'typing.Iterator':
            assert len(t.args) == 1, t.args
            type_param = t.args[0]
            inner_c_type = GetCType(type_param)
            c_type = 'ListIter<%s>' % inner_c_type

        else:
            parts = t.type.fullname.split('.')
            c_type = '%s::%s' % (parts[-2], parts[-1])

            # note: fullname => 'parse.Lexer'; name => 'Lexer'
            base_class_names = [b.type.fullname for b in t.type.bases]

            # Check base class for pybase.SimpleObj so we can output
            # expr_asdl::tok_t instead of expr_asdl::tok_t*.  That is a enum, while
            # expr_t is a "regular base class".
            # NOTE: Could we avoid the typedef?  If it's SimpleObj, just generate
            # tok_e instead?

            if 'asdl.pybase.SimpleObj' not in base_class_names:
                is_pointer = True

    elif isinstance(t, TupleType):
        inner_c_types = [GetCType(inner) for inner in t.items]
        c_type = 'Tuple%d<%s>' % (len(t.items), ', '.join(inner_c_types))
        is_pointer = True

    elif isinstance(t, UnionType):  # Optional[T]

        # Special case for Optional[IOError_OSError]
        # == Union[IOError, OSError, None]

        num_items = len(t.items)

        if num_items == 3:
            t0 = t.items[0]
            t1 = t.items[1]
            t2 = t.items[2]

            t0_name = t0.type.fullname
            t1_name = t1.type.fullname

            if t0_name != 'builtins.IOError':
                raise NotImplementedError(
                    'Expected Union[IOError, OSError, None]: t0 = %s' %
                    t0_name)

            if t1_name != 'builtins.OSError':
                raise NotImplementedError(
                    'Expected Union[IOError, OSError, None]: t1 = %s' %
                    t1_name)

            if not isinstance(t2, NoneTyp):
                raise NotImplementedError(
                    'Expected Union[IOError, OSError, None]')

            c_type = 'IOError_OSError'
            is_pointer = True

        elif num_items == 2:

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
                if (t0_name == 'builtins.IOError' and
                        t1_name == 'builtins.OSError'):
                    c_type = 'IOError_OSError'
                    is_pointer = True

            if c_type is None:
                raise NotImplementedError('Unexpected Union type %s' % t)

        else:
            raise NotImplementedError(
                'Expected 2 or 3 items in Union, got %s' % num_items)

    else:
        raise NotImplementedError('MyPy type: %s %s' % (type(t), t))

    if is_pointer:
        c_type += '*'

    return c_type


def GetCReturnType(t: Type) -> Tuple[str, bool, Optional[str]]:
    """
    Returns a C string, whether the tuple-by-value optimization was applied,
    and the C type of an extra output param if the function is a generator.
    """

    c_ret_type = GetCType(t)

    # Optimization: Return tuples BY VALUE
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


def _GetNoReturn(func_name: str) -> str:
    # Avoid C++ warnings by prepending [[noreturn]]
    noreturn = ''
    if func_name in ('e_die', 'e_die_status', 'e_strict', 'e_usage', 'p_die'):
        return '[[noreturn]] '
    else:
        return ''


# name, type, is_param
LocalVar = Tuple[str, Type, bool]

# lval_type, c_type, is_managed
MemberVar = Tuple[Type, str, bool]

AllMemberVars = Dict[ClassDef, Dict[str, MemberVar]]

AllLocalVars = Dict[FuncDef, List[Tuple[str, Type]]]


class _Shared(visitor.SimpleVisitor):

    def __init__(
        self,
        types: Dict[Expression, Type],
        global_strings: 'const_pass.GlobalStrings',
        yield_out_params: Dict[FuncDef, Tuple[str, str]],  # input
        # all_member_vars:
        # - Decl for declaring members in class { }
        # - Impl for rooting context managers
        all_member_vars: Optional[AllMemberVars] = None,
    ) -> None:
        visitor.SimpleVisitor.__init__(self)

        self.types = types
        self.global_strings = global_strings
        self.yield_out_params = yield_out_params
        self.all_member_vars = all_member_vars  # for class def, and rooting

    # Primitives shared for default values

    def visit_int_expr(self, o: 'mypy.nodes.IntExpr') -> None:
        self.write(str(o.value))

    def visit_float_expr(self, o: 'mypy.nodes.FloatExpr') -> None:
        # e.g. for arg.t > 0.0
        self.write(str(o.value))

    def visit_str_expr(self, o: 'mypy.nodes.StrExpr') -> None:
        self.write(self.global_strings.GetVarName(o))

    def oils_visit_name_expr(self, o: 'mypy.nodes.NameExpr') -> None:
        if o.name == 'None':
            self.write('nullptr')
            return
        if o.name == 'True':
            self.write('true')
            return
        if o.name == 'False':
            self.write('false')
            return
        if o.name == 'self':
            self.write('this')
            return

        self.write(o.name)

    def visit_unary_expr(self, o: 'mypy.nodes.UnaryExpr') -> None:
        # e.g. a[-1] or 'not x'
        if o.op == 'not':
            op_str = '!'
        else:
            op_str = o.op
        self.write(op_str)
        self.accept(o.expr)

    def _NamespaceComment(self) -> str:
        # abstract method
        raise NotImplementedError()

    def oils_visit_mypy_file(self, o: 'mypy.nodes.MypyFile') -> None:
        mod_parts = o.fullname.split('.')
        comment = self._NamespaceComment()

        self.write_ind('namespace %s {  // %s\n', mod_parts[-1], comment)
        self.write('\n')

        #self.log('defs %s', o.defs)
        for node in o.defs:
            self.accept(node)

        self.write('\n')
        self.write_ind('}  // %s namespace %s\n', comment, mod_parts[-1])
        self.write('\n')

    def _WriteFuncParams(self,
                         func_def: FuncDef,
                         write_defaults: bool = False) -> None:
        """Write params for function/method signatures."""
        arg_types = func_def.type.arg_types
        arguments = func_def.arguments

        is_first = True  # EXCLUDING 'self'
        for arg_type, arg in zip(arg_types, arguments):
            if not is_first:
                self.write(', ')

            c_type = GetCType(arg_type)

            arg_name = arg.variable.name

            # C++ has implicit 'this'
            if arg_name == 'self':
                continue

            # int foo
            self.write('%s %s', c_type, arg_name)

            if write_defaults and arg.initializer:  # int foo = 42
                self.write(' = ')
                self.accept(arg.initializer)

            is_first = False

            if 0:
                self.log('Argument %s', arg.variable)
                self.log('  type_annotation %s', arg.type_annotation)
                # I think these are for default values
                self.log('  initializer %s', arg.initializer)
                self.log('  kind %s', arg.kind)

        # Is the function we're writing params for an iterator?
        if func_def in self.yield_out_params:
            self.write(', ')

            arg_name, c_type = self.yield_out_params[func_def]
            self.write('%s %s', c_type, arg_name)


class Decl(_Shared):

    def __init__(
        self,
        types: Dict[Expression, Type],
        global_strings: 'const_pass.GlobalStrings',
        yield_out_params: Dict[FuncDef, Tuple[str, str]],  # input
        virtual: pass_state.Virtual = None,
        all_member_vars: Optional[AllMemberVars] = None,
    ) -> None:
        _Shared.__init__(
            self,
            types,
            global_strings,
            yield_out_params,
            all_member_vars=all_member_vars,
        )
        self.virtual = virtual

    def _NamespaceComment(self) -> str:
        # abstract method
        return 'declare'

    def oils_visit_func_def(self, o: 'mypy.nodes.FuncDef') -> None:
        # Avoid C++ warnings by prepending [[noreturn]]
        noreturn = _GetNoReturn(o.name)

        virtual = ''
        if self.virtual.IsVirtual(self.current_class_name, o.name):
            virtual = 'virtual '

        # declaration inside class { }
        func_name = o.name

        # Why can't we get this Type object with self.types[o]?
        c_ret_type, _, _ = GetCReturnType(o.type.ret_type)

        self.write_ind('%s%s%s %s(', noreturn, virtual, c_ret_type, func_name)

        self._WriteFuncParams(o, write_defaults=True)
        self.write(');\n')

    def oils_visit_member_expr(self, o: 'mypy.nodes.MemberExpr') -> None:
        # In declarations, 'a.b' is only used for default argument
        # values 'a::b'
        self.accept(o.expr)
        # TODO: remove write() in Decl pass
        self.write('::')
        self.write(o.name)

    def oils_visit_assignment_stmt(self, o: 'mypy.nodes.AssignmentStmt',
                                   lval: Expression, rval: Expression) -> None:
        # Declare constant strings.  They have to be at the top level.

        # TODO: self.at_global_scope doesn't work for context managers and so forth
        if self.indent == 0 and not util.SkipAssignment(lval.name):
            c_type = GetCType(self.types[lval])
            self.write('extern %s %s;\n', c_type, lval.name)

        # TODO: we don't traverse here, so _CheckCondition() isn't called
        # e.g. x = 'a' if mylist else 'b'

    def oils_visit_constructor(self, o: ClassDef, stmt: FuncDef,
                               base_class_name: util.SymbolPath) -> None:
        self.indent += 1
        self.write_ind('%s(', o.name)
        self._WriteFuncParams(stmt, write_defaults=True)
        self.write(');\n')
        self.indent -= 1

    def oils_visit_dunder_exit(self, o: ClassDef, stmt: FuncDef,
                               base_class_name: util.SymbolPath) -> None:
        self.indent += 1
        # Turn it into a destructor with NO ARGS
        self.write_ind('~%s();\n', o.name)
        self.indent -= 1

    def oils_visit_method(self, o: ClassDef, stmt: FuncDef,
                          base_class_name: util.SymbolPath) -> None:
        self.indent += 1
        self.accept(stmt)
        self.indent -= 1

    def oils_visit_class_members(self, o: ClassDef,
                                 base_class_name: util.SymbolPath) -> None:
        # Write member variables
        self.indent += 1
        self._MemberDecl(o, base_class_name)
        self.indent -= 1

    def oils_visit_class_def(
            self, o: 'mypy.nodes.ClassDef',
            base_class_name: Optional[util.SymbolPath]) -> None:
        self.write_ind('class %s', o.name)  # block after this

        # e.g. class TextOutput : public ColorOutput
        if base_class_name:
            self.write(' : public %s',
                       join_name(base_class_name, strip_package=True))

        self.write(' {\n')
        self.write_ind(' public:\n')

        # This visits all the methods, with self.indent += 1, param
        # base_class_name, self.current_method_name

        super().oils_visit_class_def(o, base_class_name)

        self.write_ind('};\n')
        self.write('\n')

    def _GcHeaderDecl(self, o: 'mypy.nodes.ClassDef',
                      field_gc: Tuple[str, str], mask_bits: List[str]) -> None:
        if mask_bits:
            self.write_ind('\n')
            self.write_ind('static constexpr uint32_t field_mask() {\n')
            self.write_ind('  return ')
            for i, b in enumerate(mask_bits):
                if i != 0:
                    self.write('\n')
                    self.write_ind('       | ')
                self.write(b)
            self.write(';\n')
            self.write_ind('}\n')

        obj_tag, obj_arg = field_gc
        if obj_tag == 'HeapTag::FixedSize':
            obj_mask = obj_arg
            obj_header = 'ObjHeader::ClassFixed(%s, sizeof(%s))' % (obj_mask,
                                                                    o.name)
        elif obj_tag == 'HeapTag::Scanned':
            num_pointers = obj_arg
            obj_header = 'ObjHeader::ClassScanned(%s, sizeof(%s))' % (
                num_pointers, o.name)
        else:
            raise AssertionError(o.name)

        self.write('\n')
        self.write_ind('static constexpr ObjHeader obj_header() {\n')
        self.write_ind('  return %s;\n' % obj_header)
        self.write_ind('}\n')

    def _MemberDecl(self, o: 'mypy.nodes.ClassDef',
                    base_class_name: util.SymbolPath) -> None:
        member_vars = self.all_member_vars[o]

        # List of field mask expressions
        mask_bits = []
        if self.virtual.CanReorderFields(split_py_name(o.fullname)):
            # No inheritance, so we are free to REORDER member vars, putting
            # pointers at the front.

            pointer_members = []
            non_pointer_members = []

            for name in member_vars:
                _, c_type, is_managed = member_vars[name]
                if is_managed:
                    pointer_members.append(name)
                else:
                    non_pointer_members.append(name)

            # So we declare them in the right order
            sorted_member_names = pointer_members + non_pointer_members

            field_gc = ('HeapTag::Scanned', str(len(pointer_members)))
        else:
            # Has inheritance

            # The field mask of a derived class is unioned with its base's
            # field mask.
            if base_class_name:
                mask_bits.append(
                    '%s::field_mask()' %
                    join_name(base_class_name, strip_package=True))

            for name in sorted(member_vars):
                _, c_type, is_managed = member_vars[name]
                if is_managed:
                    mask_bits.append('maskbit(offsetof(%s, %s))' %
                                     (o.name, name))

            # A base class with no fields has kZeroMask.
            if not base_class_name and not mask_bits:
                mask_bits.append('kZeroMask')

            sorted_member_names = sorted(member_vars)

            field_gc = ('HeapTag::FixedSize', 'field_mask()')

        # Write member variables

        #log('MEMBERS for %s: %s', o.name, list(self.member_vars.keys()))
        if len(member_vars):
            if base_class_name:
                self.write('\n')  # separate from functions

            for name in sorted_member_names:
                _, c_type, _ = member_vars[name]
                # use default zero initialization for all members
                # (context managers may be on the stack)
                self.write_ind('%s %s{};\n', c_type, name)

        # Context managers aren't GC objects
        if not _IsContextManager(self.current_class_name):
            self._GcHeaderDecl(o, field_gc, mask_bits)

        self.write('\n')
        self.write_ind('DISALLOW_COPY_AND_ASSIGN(%s)\n', o.name)


class Impl(_Shared):

    def __init__(
            self,
            types: Dict[Expression, Type],
            global_strings: 'const_pass.GlobalStrings',
            yield_out_params: Dict[FuncDef, Tuple[str, str]],  # input
            local_vars: Optional[AllLocalVars] = None,
            all_member_vars: Optional[AllMemberVars] = None,
            dot_exprs: Optional['ir_pass.DotExprs'] = None,
            stack_roots_warn: Optional[int] = None,
            stack_roots: Optional[pass_state.StackRoots] = None) -> None:
        _Shared.__init__(self,
                         types,
                         global_strings,
                         yield_out_params,
                         all_member_vars=all_member_vars)
        self.local_vars = local_vars

        # Computed in previous passes
        self.dot_exprs = dot_exprs
        self.stack_roots_warn = stack_roots_warn
        self.stack_roots = stack_roots

        # Traversal state used to to create an EAGER List<T>
        self.yield_eager_assign: Dict[AssignmentStmt, Tuple[str, str]] = {}
        self.yield_eager_for: Dict[ForStmt, Tuple[str, str]] = {}

        self.yield_assign_node: Optional[AssignmentStmt] = None
        self.yield_for_node: Optional[ForStmt] = None

        # More Traversal state
        self.current_func_node: Optional[FuncDef] = None

        self.unique_id = 0

    def _NamespaceComment(self) -> str:
        # abstract method
        return 'define'

    def oils_visit_func_def(self, o: 'mypy.nodes.FuncDef') -> None:
        if self.current_class_name:
            # definition looks like
            # void Class::method(...);
            func_name = join_name((self.current_class_name[-1], o.name))
            noreturn = ''
        else:
            func_name = o.name
            noreturn = _GetNoReturn(o.name)

        self.write('\n')

        # Why can't we get this Type object with self.types[o]?
        c_ret_type, _, _ = GetCReturnType(o.type.ret_type)

        self.write_ind('%s%s %s(', noreturn, c_ret_type, func_name)

        self.current_func_node = o
        self._WriteFuncParams(o, write_defaults=False)

        self.write(') ')
        arg_names = [arg.variable.name for arg in o.arguments]
        #log('arg_names %s', arg_names)
        #log('local_vars %s', self.local_vars[o])
        local_var_list: List[LocalVar] = []
        for (lval_name, lval_type) in self.local_vars[o]:
            local_var_list.append((lval_name, lval_type, lval_name
                                   in arg_names))

        self.write('{\n')

        self.indent += 1
        self._WriteLocals(local_var_list)
        self._WriteBody(o.body.body)
        self.indent -= 1

        self.write('}\n')

        self.current_func_node = None

    #
    # Visit methods
    #

    def visit_yield_expr(self, o: 'mypy.nodes.YieldExpr') -> None:
        assert self.current_func_node in self.yield_out_params
        self.write('%s->append(',
                   self.yield_out_params[self.current_func_node][0])
        self.accept(o.expr)
        self.write(')')

    def _WriteArgList(self, args: List[Expression]) -> None:
        self.write('(')
        for i, arg in enumerate(args):
            if i != 0:
                self.write(', ')
            self.accept(arg)

        # Pass an extra arg like my_generator(42, &accum)
        #
        # Two cases:
        #   ForStmt:         for y in generator(42): =>
        #                    generator(42, &y)
        #   AssignmentStmt:  it = generator(42)     =>
        #                    List<int> _iter_buf_it;
        #                    generator(42, &iter_buf_it);   # eagerly append

        eager_pair = (self.yield_eager_assign.get(self.yield_assign_node) or
                      self.yield_eager_for.get(self.yield_for_node))

        if eager_pair:
            if len(args) > 0:
                self.write(', ')

            eager_list_name, _ = eager_pair
            self.write('&%s', eager_list_name)

        self.write(')')

    def oils_visit_member_expr(self, o: 'mypy.nodes.MemberExpr') -> None:
        dot_expr = self.dot_exprs[o]

        if isinstance(dot_expr, pass_state.StackObjectMember):
            op = '.'

        elif (isinstance(dot_expr, pass_state.StaticObjectMember) or
              isinstance(dot_expr, pass_state.ModuleMember)):
            op = '::'

        elif isinstance(dot_expr, pass_state.HeapObjectMember):
            op = '->'

        else:
            raise AssertionError()

        self.accept(o.expr)
        self.write(op)

        if o.name == 'errno':
            # e->errno -> e->errno_ to avoid conflict with C macro
            self.write('errno_')
        else:
            self.write('%s', o.name)

    def _IsInstantiation(self, o: 'mypy.nodes.CallExpr') -> bool:
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

            # e.g. str(i) is a free function
            if (callee_name not in ('str', 'bool', 'float') and
                    'BigInt' not in callee_name and
                    isinstance(ret_type, Instance)):

                ret_type_name = ret_type.type.name

                # HACK: Const is the callee; expr__Const is the return type
                if (ret_type_name == callee_name or
                        ret_type_name.endswith('__' + callee_name)):
                    return True

        return False

    def _ProbeExpr(self, o: 'mypy.nodes.CallExpr') -> None:
        assert len(o.args) >= 2 and len(o.args) < 13, o.args
        assert isinstance(o.args[0], mypy.nodes.StrExpr), o.args[0]
        assert isinstance(o.args[1], mypy.nodes.StrExpr), o.args[1]
        arity = len(o.args) - 2
        macro = 'DTRACE_PROBE'
        if arity > 0:
            macro = 'DTRACE_PROBE%d' % arity

        self.write('%s(%s, %s', macro, o.args[0].value, o.args[1].value)

        for arg in o.args[2:]:
            arg_type = self.types[arg]
            self.write(', ')
            if (isinstance(arg_type, Instance) and
                    arg_type.type.fullname == 'builtins.str'):
                self.write('%s->data()' % arg.name)
            else:
                self.accept(arg)

        self.write(')')

    def _LogExpr(self, o: 'mypy.nodes.CallExpr') -> None:
        args = o.args
        if len(args) == 1:  # log(CONST)
            self.write('mylib::print_stderr(')
            self.accept(args[0])
            self.write(')')
            return

        quoted_fmt = PythonStringLiteral(args[0].value)

        self.write('mylib::print_stderr(StrFormat(%s, ' % quoted_fmt)
        for i, arg in enumerate(args[1:]):
            if i != 0:
                self.write(', ')
            self.accept(arg)
        self.write('))')

    def visit_call_expr(self, o: 'mypy.nodes.CallExpr') -> None:
        if o.callee.name == 'probe':
            self._ProbeExpr(o)
            return

        if o.callee.name == 'isinstance':
            self.report_error(o, 'isinstance() not allowed')
            return

        #    return cast(ShArrayLiteral, tok)
        # -> return static_cast<ShArrayLiteral*>(tok)

        # TODO: Consolidate this with AssignmentExpr logic.
        if o.callee.name == 'cast':
            call = o
            type_expr = call.args[0]

            subtype_name = _GetCTypeForCast(type_expr)
            cast_kind = _GetCastKind(self.module_path, subtype_name)
            self.write('%s<%s>(', cast_kind, subtype_name)
            self.accept(call.args[1])  # variable being casted
            self.write(')')
            return

        # Translate printf-style varargs:
        #
        # log('foo %s', x)
        #   =>
        # log(StrFormat('foo %s', x))
        if o.callee.name == 'log':
            self._LogExpr(o)
            return

        callee_name = o.callee.name

        if isinstance(o.callee, MemberExpr) and callee_name == 'next':
            self.accept(o.callee.expr)
            self.write('.iterNext')
            self._WriteArgList(o.args)
            return

        if self._IsInstantiation(o):
            self.write('Alloc<')
            self.accept(o.callee)
            self.write('>')
            self._WriteArgList(o.args)
            return

        # Namespace.
        if callee_name == 'int':  # int('foo') in Python conflicts with keyword
            self.write('to_int')
        elif callee_name == 'float':
            self.write('to_float')
        elif callee_name == 'bool':
            self.write('to_bool')
        else:
            self.accept(o.callee)  # could be f() or obj.method()

        self._WriteArgList(o.args)

        # TODO: we could check that keyword arguments are passed as named args?
        #self.log('  arg_kinds %s', o.arg_kinds)
        #self.log('  arg_names %s', o.arg_names)

    def visit_op_expr(self, o: 'mypy.nodes.OpExpr') -> None:
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
            self.write('str_concat(')
            self.accept(o.left)
            self.write(', ')
            self.accept(o.right)
            self.write(')')
            return

        # 'abc' * 3
        if left_ctype == 'BigStr*' and right_ctype == 'int' and c_op == '*':
            self.write('str_repeat(')
            self.accept(o.left)
            self.write(', ')
            self.accept(o.right)
            self.write(')')
            return

        # [None] * 3  =>  list_repeat(None, 3)
        if (left_ctype.startswith('List<') and right_ctype == 'int' and
                c_op == '*'):
            self.write('list_repeat(')
            self.accept(o.left.items[0])
            self.write(', ')
            self.accept(o.right)
            self.write(')')
            return

        # RHS can be primitive or tuple
        if left_ctype == 'BigStr*' and c_op == '%':
            self.write('StrFormat(')
            if isinstance(o.left, StrExpr):
                self.write(PythonStringLiteral(o.left.value))
            else:
                self.accept(o.left)
            #log('right_type %s', right_type)
            if 0:
                if isinstance(right_type, Instance):
                    fmt_types: List[Type] = [right_type]
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
                    self.write(', ')
                    self.accept(item)
            else:  # '[%s]' % x
                self.write(', ')
                self.accept(o.right)

            self.write(')')
            return

        # These parens are sometimes extra, but sometimes required.  Example:
        #
        # if ((a and (false or true))) {  # right
        # vs.
        # if (a and false or true)) {  # wrong
        self.write('(')
        self.accept(o.left)
        self.write(' %s ', c_op)
        self.accept(o.right)
        self.write(')')

    def visit_comparison_expr(self, o: 'mypy.nodes.ComparisonExpr') -> None:
        # Make sure it's binary
        assert len(o.operators) == 1, o.operators
        assert len(o.operands) == 2, o.operands

        operator = o.operators[0]
        left = o.operands[0]
        right = o.operands[1]

        # Assume is and is not are for None / nullptr comparison.
        if operator == 'is':  # foo is None => foo == nullptr
            self.accept(o.operands[0])
            self.write(' == ')
            self.accept(o.operands[1])
            return

        if operator == 'is not':  # foo is not None => foo != nullptr
            self.accept(o.operands[0])
            self.write(' != ')
            self.accept(o.operands[1])
            return

        t0 = self.types[left]
        t1 = self.types[right]

        # 0: not a special case
        # 1: str
        # 2: Optional[str] which is Union[str, None]
        left_type_i = 0  # not a special case
        right_type_i = 0  # not a special case

        if IsStr(t0):
            left_type_i = 1
        elif (isinstance(t0, UnionType) and len(t0.items) == 2 and
              IsStr(t0.items[0]) and isinstance(t0.items[1], NoneTyp)):
            left_type_i = 2

        if IsStr(t1):
            right_type_i = 1
        elif (isinstance(t1, UnionType) and len(t1.items) == 2 and
              IsStr(t1.items[0]) and isinstance(t1.items[1], NoneTyp)):
            right_type_i = 2

        #self.log('left_type_i %s right_type_i %s', left_type, right_type)

        if left_type_i > 0 and right_type_i > 0 and operator in ('==', '!='):
            if operator == '!=':
                self.write('!(')

            # NOTE: This could also be str_equals(left, right)?  Does it make a
            # difference?
            if left_type_i > 1 or right_type_i > 1:
                self.write('maybe_str_equals(')
            else:
                self.write('str_equals(')
            self.accept(left)
            self.write(', ')
            self.accept(right)
            self.write(')')

            if operator == '!=':
                self.write(')')
            return

        # Note: we could get rid of this altogether and rely on C++ function
        # overloading.  But somehow I like it more explicit, closer to C (even
        # though we use templates).
        contains_func = _ContainsFunc(t1)

        if operator == 'in':
            if isinstance(right, TupleExpr):
                left_type = self.types[left]

                equals_func = _EqualsFunc(left_type)

                # x in (1, 2, 3) => (x == 1 || x == 2 || x == 3)
                self.write('(')

                for i, item in enumerate(right.items):
                    if i != 0:
                        self.write(' || ')

                    if equals_func:
                        self.write('%s(' % equals_func)
                        self.accept(left)
                        self.write(', ')
                        self.accept(item)
                        self.write(')')
                    else:
                        self.accept(left)
                        self.write(' == ')
                        self.accept(item)

                self.write(')')
                return

            assert contains_func, "RHS of 'in' has type %r" % t1
            # x in mylist => list_contains(mylist, x)
            self.write('%s(', contains_func)
            self.accept(right)
            self.write(', ')
            self.accept(left)
            self.write(')')
            return

        if operator == 'not in':
            if isinstance(right, TupleExpr):
                left_type = self.types[left]
                equals_func = _EqualsFunc(left_type)

                # x not in (1, 2, 3) => (x != 1 && x != 2 && x != 3)
                self.write('(')

                for i, item in enumerate(right.items):
                    if i != 0:
                        self.write(' && ')

                    if equals_func:
                        self.write('!%s(' % equals_func)
                        self.accept(left)
                        self.write(', ')
                        self.accept(item)
                        self.write(')')
                    else:
                        self.accept(left)
                        self.write(' != ')
                        self.accept(item)

                self.write(')')
                return

            assert contains_func, t1

            # x not in mylist => !list_contains(mylist, x)
            self.write('!%s(', contains_func)
            self.accept(right)
            self.write(', ')
            self.accept(left)
            self.write(')')
            return

        # Default case
        self.accept(o.operands[0])
        self.write(' %s ', o.operators[0])
        self.accept(o.operands[1])

    def _WriteListElements(self,
                           items: List[Expression],
                           sep: str = ', ') -> None:
        # sep may be 'COMMA' for a macro
        self.write('{')
        for i, item in enumerate(items):
            if i != 0:
                self.write(sep)
            self.accept(item)
        self.write('}')

    def visit_list_expr(self, o: 'mypy.nodes.ListExpr') -> None:
        list_type = self.types[o]
        #self.log('**** list_type = %s', list_type)
        c_type = GetCType(list_type)

        item_type = list_type.args[0]  # int for List[int]
        item_c_type = GetCType(item_type)

        assert c_type.endswith('*'), c_type
        c_type = c_type[:-1]  # HACK TO CLEAN UP

        if len(o.items) == 0:
            self.write('Alloc<%s>()' % c_type)
        else:
            self.write('NewList<%s>(std::initializer_list<%s>' %
                       (item_c_type, item_c_type))
            self._WriteListElements(o.items)
            self.write(')')

    def visit_dict_expr(self, o: 'mypy.nodes.DictExpr') -> None:
        dict_type = self.types[o]
        c_type = GetCType(dict_type)
        assert c_type.endswith('*'), c_type
        c_type = c_type[:-1]  # HACK TO CLEAN UP

        key_type, val_type = dict_type.args
        key_c_type = GetCType(key_type)
        val_c_type = GetCType(val_type)

        self.write('Alloc<%s>(' % c_type)
        #self.write('NewDict<%s, %s>(' % (key_c_type, val_c_type))
        if o.items:
            keys = [k for k, _ in o.items]
            values = [v for _, v in o.items]

            self.write('std::initializer_list<%s>' % key_c_type)
            self._WriteListElements(keys)
            self.write(', ')

            self.write('std::initializer_list<%s>' % val_c_type)
            self._WriteListElements(values)

        self.write(')')

    def visit_tuple_expr(self, o: 'mypy.nodes.TupleExpr') -> None:
        tuple_type = self.types[o]
        c_type = GetCType(tuple_type)
        assert c_type.endswith('*'), c_type
        c_type = c_type[:-1]  # HACK TO CLEAN UP

        self.write('(Alloc<%s>(' % c_type)
        for i, item in enumerate(o.items):
            if i != 0:
                self.write(', ')
            self.accept(item)
        self.write('))')

    def visit_index_expr(self, o: 'mypy.nodes.IndexExpr') -> None:
        self.accept(o.base)

        #base_type = self.types[o.base]
        #self.log('*** BASE TYPE %s', base_type)

        if isinstance(o.index, SliceExpr):
            self.accept(o.index)  # method call
        else:
            # it's hard syntactically to do (*a)[0], so do it this way.
            if util.SMALL_STR:
                self.write('.at(')
            else:
                self.write('->at(')

            self.accept(o.index)
            self.write(')')

    def visit_slice_expr(self, o: 'mypy.nodes.SliceExpr') -> None:
        self.write('->slice(')
        if o.begin_index:
            self.accept(o.begin_index)
        else:
            self.write('0')  # implicit beginning

        if o.end_index:
            self.write(', ')
            self.accept(o.end_index)

        if o.stride:
            if not o.begin_index or not o.end_index:
                raise AssertionError(
                    'Stride only supported with beginning and ending index')

            self.write(', ')
            self.accept(o.stride)

        self.write(')')

    def visit_conditional_expr(self, o: 'mypy.nodes.ConditionalExpr') -> None:
        if not _CheckCondition(o.cond, self.types):
            self.report_error(
                o,
                "Use explicit len(obj) or 'obj is not None' for mystr, mylist, mydict"
            )
            return

        # 0 if b else 1 -> b ? 0 : 1
        self.accept(o.cond)
        self.write(' ? ')
        self.accept(o.if_expr)
        self.write(' : ')
        self.accept(o.else_expr)

    def _WriteTupleUnpacking(self,
                             temp_name: str,
                             lval_items: List[Expression],
                             item_types: List[Type],
                             is_return: bool = False) -> None:
        """Used by assignment and for loops.

        is_return is a special case for:

            # return Tuple2<A, B> by VALUE, not Tuple2<A, B>* pointer
            a, b = myfunc()
        """
        for i, (lval_item, item_type) in enumerate(zip(lval_items,
                                                       item_types)):
            if isinstance(lval_item, NameExpr):
                if util.SkipAssignment(lval_item.name):
                    continue
                self.write_ind('%s', lval_item.name)
            else:
                # Could be MemberExpr like self.foo, self.bar = baz
                self.write_ind('')
                self.accept(lval_item)

            # Tuples that are return values aren't pointers
            op = '.' if is_return else '->'
            self.write(' = %s%sat%d();\n', temp_name, op, i)  # RHS

    def _WriteTupleUnpackingInLoop(self, temp_name: str,
                                   lval_items: List[Expression],
                                   item_types: List[Type]) -> None:
        for i, (lval_item, item_type) in enumerate(zip(lval_items,
                                                       item_types)):
            c_item_type = GetCType(item_type)

            if isinstance(lval_item, NameExpr):
                if util.SkipAssignment(lval_item.name):
                    continue

                self.write_ind('%s %s', c_item_type, lval_item.name)
            else:
                # Could be MemberExpr like self.foo, self.bar = baz
                self.write_ind('')
                self.accept(lval_item)

            op = '->'
            self.write(' = %s%sat%d();\n', temp_name, op, i)  # RHS

            # Note: it would be nice to eliminate these roots, just like
            # StackRoots _for() below
            if isinstance(lval_item, NameExpr):
                if CTypeIsManaged(c_item_type) and not self.stack_roots:
                    self.write_ind('StackRoot _unpack_%d(&%s);\n' %
                                   (i, lval_item.name))

    def _AssignNewDictImpl(self, lval: Expression, prefix: str = '') -> None:
        """Translate NewDict() -> Alloc<Dict<K, V>>

        This function is a specal case because the RHS need TYPES from the LHS.

        e.g. here is how we make ORDERED dictionaries, which can't be done with {}:

           d = NewDict()  # type: Dict[int, int]

        -> one of

           auto* d = Alloc<Dict<int, int>>();  # declare
           d = Alloc<Dict<int, int>>();        # mutate

        We also have:

            self.d = NewDict() 
        ->
            this->d = Alloc<Dict<int, int>)();
        """
        lval_type = self.types[lval]
        #self.log('lval type %s', lval_type)

        # Fix for Dict[str, value]? in ASDL
        if (isinstance(lval_type, UnionType) and len(lval_type.items) == 2 and
                isinstance(lval_type.items[1], NoneTyp)):
            lval_type = lval_type.items[0]

        c_type = GetCType(lval_type)
        assert c_type.endswith('*')
        self.write('Alloc<%s>()', c_type[:-1])

    def _AssignCastImpl(self, o: 'mypy.nodes.AssignmentStmt',
                        lval: Expression) -> None:
        """
        is_downcast_and_shadow idiom:
        
           src = cast(source__SourcedFile, UP_src)
        -> source__SourcedFile* src = static_cast<source__SourcedFile>(UP_src)
        """
        assert isinstance(lval, NameExpr)
        call = o.rvalue
        type_expr = call.args[0]
        subtype_name = _GetCTypeForCast(type_expr)

        cast_kind = _GetCastKind(self.module_path, subtype_name)

        is_downcast_and_shadow = False
        to_cast = call.args[1]
        if isinstance(to_cast, NameExpr):
            if to_cast.name.startswith('UP_'):
                is_downcast_and_shadow = True

        if is_downcast_and_shadow:
            # Declare NEW local variable inside case, which shadows it
            self.write_ind('%s %s = %s<%s>(', subtype_name, lval.name,
                           cast_kind, subtype_name)
        else:
            # Normal variable
            self.write_ind('%s = %s<%s>(', lval.name, cast_kind, subtype_name)

        self.accept(call.args[1])  # variable being casted
        self.write(');\n')

    def _AssignToGenerator(self, o: 'mypy.nodes.AssignmentStmt',
                           lval: Expression, rval_type: Type) -> None:
        """
        it_f = f(42)

        translates to

        List<int> _iter_buf_it;
        f(42, &_iter_buf_it);
        """
        # We're calling a generator. Create a temporary List<T> on the stack
        # to accumulate the results in one big batch, then wrap it in
        # ListIter<T>.
        assert len(rval_type.args) == 1, rval_type.args
        c_type = GetCType(rval_type)

        type_param = rval_type.args[0]
        inner_c_type = GetCType(type_param)

        eager_list_name = 'YIELD_%s' % lval.name
        eager_list_type = 'List<%s>*' % inner_c_type

        # write the variable to accumulate into
        self.write_ind('List<%s> %s;\n', inner_c_type, eager_list_name)

        # AssignmentStmt key, like:
        #     it_f = f()
        # maybe call them self.generator_func, generator_assign
        # In MyPy, the type is Iterator though
        self.yield_eager_assign[o] = (eager_list_name, eager_list_type)
        self.write_ind('')

        self.yield_assign_node = o  # AssignmentStmt
        self.accept(o.rvalue)
        self.yield_assign_node = None

        self.write(';\n')

        self.write_ind('%s %s(&%s);\n', c_type, lval.name, eager_list_name)

    def oils_visit_assign_to_listcomp(self, lval: NameExpr,
                                      left_expr: Expression,
                                      index_expr: Expression, seq: Expression,
                                      cond: Expression) -> None:
        """
        Special case for list comprehensions.  Note that the LHS MUST be on the
        LHS, so we can append to it.
        
        y = [i+1 for i in x[1:] if i]
          =>
        y = []
        for i in x[1:]:
          if i:
            y.append(i+1)
        (but in C++)
        """
        self.write_ind('%s = ', lval.name)

        # BUG: can't use this to filter
        # results = [x for x in results]
        if isinstance(seq, NameExpr) and seq.name == lval.name:
            raise AssertionError(
                "Can't use var %r in list comprehension because it would "
                "be overwritten" % lval.name)

        c_type = GetCType(self.types[lval])
        # Write empty container as initialization.
        assert c_type.endswith('*'), c_type  # Hack
        self.write('Alloc<%s>();\n' % c_type[:-1])

        over_type = self.types[seq]

        if over_type.type.fullname == 'builtins.list':
            c_type = GetCType(over_type)
            # remove *
            assert c_type.endswith('*'), c_type
            c_iter_type = c_type.replace('List', 'ListIter', 1)[:-1]
        else:
            # List comprehension over dictionary not implemented
            c_iter_type = 'TODO_DICT'

        self.write_ind('for (%s it(', c_iter_type)
        self.accept(seq)
        self.write('); !it.Done(); it.Next()) {\n')

        item_type = over_type.args[0]  # get 'int' from 'List<int>'

        if isinstance(item_type, Instance):
            self.write_ind('  %s ', GetCType(item_type))
            # TODO(StackRoots): for ch in 'abc'
            self.accept(index_expr)
            self.write(' = it.Value();\n')

        elif isinstance(item_type, TupleType):  # [x for x, y in pairs]
            c_item_type = GetCType(item_type)

            if isinstance(index_expr, TupleExpr):
                temp_name = 'tup%d' % self.unique_id
                self.unique_id += 1
                self.write_ind('  %s %s = it.Value();\n', c_item_type,
                               temp_name)

                self.indent += 1

                # list comp
                self._WriteTupleUnpackingInLoop(temp_name, index_expr.items,
                                                item_type.items)

                self.indent -= 1
            else:
                raise AssertionError()

        else:
            raise AssertionError('Unexpected type %s' % item_type)

        if cond is not None:
            self.indent += 1
            self.write_ind('if (')
            self.accept(cond)
            self.write(') {\n')

        self.write_ind('  %s->append(', lval.name)
        self.accept(left_expr)
        self.write(');\n')

        if cond:
            self.write_ind('}\n')
            self.indent -= 1

        self.write_ind('}\n')

    def oils_visit_assignment_stmt(self, o: 'mypy.nodes.AssignmentStmt',
                                   lval: Expression, rval: Expression) -> None:

        # GLOBAL CONSTANTS - Avoid Alloc<T>, since that can't be done until main().
        if self.indent == 0:
            assert isinstance(lval, NameExpr), lval
            if util.SkipAssignment(lval.name):
                return
            #self.log('    GLOBAL: %s', lval.name)

            lval_type = self.types[lval]

            # Global
            #   L = [1, 2]  # type: List[int]
            if isinstance(rval, ListExpr):
                item_type = lval_type.args[0]
                item_c_type = GetCType(item_type)

                # Any constant strings will have already been written
                # TODO: Assert that every item is a constant?
                self.write('GLOBAL_LIST(%s, %s, %d, ', lval.name, item_c_type,
                           len(rval.items))

                self._WriteListElements(rval.items, sep=' COMMA ')

                self.write(');\n')
                return

            # Global
            #   D = {"foo": "bar"}  # type: Dict[str, str]
            if isinstance(rval, DictExpr):
                key_type, val_type = lval_type.args

                key_c_type = GetCType(key_type)
                val_c_type = GetCType(val_type)

                dict_expr = rval
                self.write('GLOBAL_DICT(%s, %s, %s, %d, ', lval.name,
                           key_c_type, val_c_type, len(dict_expr.items))

                keys = [k for k, _ in dict_expr.items]
                values = [v for _, v in dict_expr.items]

                self._WriteListElements(keys, sep=' COMMA ')
                self.write(', ')
                self._WriteListElements(values, sep=' COMMA ')

                self.write(');\n')
                return

            # We could do GcGlobal<> for ASDL classes, but Oils doesn't use them
            if isinstance(rval, CallExpr):
                self.report_error(
                    o,
                    "Can't initialize objects at the top level, only BigStr List Dict"
                )
                return

            # myconst = 1 << 3  =>  myconst = 1 << 3  is currently allowed

        #
        # Non-top-level
        #

        if isinstance(rval, CallExpr):
            callee = rval.callee

            if callee.name == 'NewDict':
                self.write_ind('')

                # Hack for non-members - why does this work?
                # Tests cases in mycpp/examples/containers.py
                if (not isinstance(lval, MemberExpr) and
                        self.current_func_node is None):
                    self.write('auto* ')

                self.accept(lval)
                self.write(' = ')
                self._AssignNewDictImpl(lval)  # uses lval, not rval
                self.write(';\n')
                return

            if callee.name == 'cast':
                self._AssignCastImpl(o, lval)
                return

            rval_type = self.types[rval]
            if (isinstance(rval_type, Instance) and
                    rval_type.type.fullname == 'typing.Iterator'):
                self._AssignToGenerator(o, lval, rval_type)
                return

        if isinstance(lval, NameExpr):
            lval_type = self.types[lval]
            #c_type = GetCType(lval_type, local=self.indent != 0)
            c_type = GetCType(lval_type)

            if self.at_global_scope:
                # globals always get a type -- they're not mutated
                self.write_ind('%s %s = ', c_type, lval.name)
            else:
                # local declarations are "hoisted" to the top of the function
                self.write_ind('%s = ', lval.name)

            self.accept(rval)
            self.write(';\n')
            return

        if isinstance(lval, MemberExpr):  # self.x = foo
            self.write_ind('')
            self.accept(lval)
            self.write(' = ')
            self.accept(rval)
            self.write(';\n')
            return

        if isinstance(lval, IndexExpr):  # a[x] = 1
            # d->set(x, 1) for both List and Dict
            self.write_ind('')
            self.accept(lval.base)
            self.write('->set(')
            self.accept(lval.index)
            self.write(', ')
            self.accept(rval)
            self.write(');\n')
            return

        if isinstance(lval, TupleExpr):
            # An assignment to an n-tuple turns into n+1 statements.  Example:
            #
            # x, y = mytuple
            #
            # Tuple2<int, BigStr*> tup1 = mytuple
            # int x = tup1->at0()
            # BigStr* y = tup1->at1()

            rvalue_type = self.types[rval]

            # type alias upgrade for MyPy 0.780
            if isinstance(rvalue_type, TypeAliasType):
                rvalue_type = rvalue_type.alias.target

            c_type = GetCType(rvalue_type)

            is_return = (isinstance(rval, CallExpr) and
                         rval.callee.name != "next")
            if is_return:
                assert c_type.endswith('*')
                c_type = c_type[:-1]

            temp_name = 'tup%d' % self.unique_id
            self.unique_id += 1
            self.write_ind('%s %s = ', c_type, temp_name)

            self.accept(rval)
            self.write(';\n')

            # assignment
            self._WriteTupleUnpacking(temp_name,
                                      lval.items,
                                      rvalue_type.items,
                                      is_return=is_return)
            return

        raise AssertionError(lval)

    def _WriteBody(self, body: List[Statement]) -> None:
        """Write a block without the { }."""
        for stmt in body:
            self.accept(stmt)

    def oils_visit_for_stmt(self, o: 'mypy.nodes.ForStmt',
                            func_name: Optional[str]) -> None:
        if 0:
            self.log('ForStmt')
            self.log('  index_type %s', o.index_type)
            self.log('  inferred_item_type %s', o.inferred_item_type)
            self.log('  inferred_iterator_type %s', o.inferred_iterator_type)

        # special case: 'for i in xrange(3)'
        if func_name == 'xrange':
            index_name = o.index.name
            args = o.expr.args
            num_args = len(args)

            if num_args == 1:  # xrange(end)
                self.write_ind('for (int %s = 0; %s < ', index_name,
                               index_name)
                self.accept(args[0])
                self.write('; ++%s) ', index_name)

            elif num_args == 2:  # xrange(being, end)
                self.write_ind('for (int %s = ', index_name)
                self.accept(args[0])
                self.write('; %s < ', index_name)
                self.accept(args[1])
                self.write('; ++%s) ', index_name)

            elif num_args == 3:  # xrange(being, end, step)
                # Special case to detect a step of -1.  This is a static
                # heuristic, because it could be negative dynamically.
                # TODO: could add an API like mylib.reverse_xrange()
                step = args[2]
                if isinstance(step, UnaryExpr) and step.op == '-':
                    comparison_op = '>'
                else:
                    comparison_op = '<'

                self.write_ind('for (int %s = ', index_name)
                self.accept(args[0])
                self.write('; %s %s ', index_name, comparison_op)
                self.accept(args[1])
                self.write('; %s += ', index_name)
                self.accept(step)
                self.write(') ')

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

        if 0:
            log("***** OVER %s %s", over_type, dir(over_type))
            t = over_type.type
            log("***** t %s %s", t, dir(t))
            bases = t.bases
            # Look for string and dict!
            log("=== bases %s %s", bases, dir(bases))

            #self.log('  iterating over type %s', over_type)
            #self.log('  iterating over type %s', over_type.type.fullname)

        eager_list_name: Optional[str] = None

        over_list = False
        over_dict = False

        if over_type.type.fullname == 'builtins.list':
            over_list = True
            container_base_type = over_type

        if over_type.type.fullname == 'builtins.dict':
            over_dict = True
            container_base_type = over_type

        # now check base classes
        for base_type in over_type.type.bases:
            n = base_type.type.fullname
            if n == 'builtins.list':
                over_list = True
                container_base_type = base_type
            elif n == 'builtins.dict':
                over_dict = True
                container_base_type = base_type

        assert not (over_dict and over_list)

        if over_list:
            c_type = GetCType(over_type)
            assert c_type.endswith('*'), c_type
            inner_c_type = GetCType(container_base_type.args[0])
            c_iter_type = 'ListIter<%s>' % inner_c_type

            # ReverseListIter!
            if reverse:
                c_iter_type = 'Reverse' + c_iter_type

        elif over_dict:
            key_c_type = GetCType(container_base_type.args[0])
            val_c_type = GetCType(container_base_type.args[1])
            c_iter_type = 'DictIter<%s, %s>' % (key_c_type, val_c_type)
            assert not reverse

        elif over_type.type.fullname == 'builtins.str':
            c_iter_type = 'StrIter'
            assert not reverse  # can't reverse iterate over string yet

        elif over_type.type.fullname == 'typing.Iterator':
            # We're iterating over a generator. Create a temporary List<T> on
            # the stack to accumulate the results in one big batch.
            c_iter_type = GetCType(over_type)

            assert len(over_type.args) == 1, over_type.args
            inner_c_type = GetCType(over_type.args[0])

            # eager_list_name is used below
            eager_list_name = 'YIELD_for_%d' % self.unique_id
            eager_list_type = 'List<%s>*' % inner_c_type
            self.unique_id += 1

            self.write_ind('List<%s> %s;\n', inner_c_type, eager_list_name)
            self.write_ind('')

            # ForStmt - could be self.generator_for_stmt
            #
            # for x in my_generator(42):
            #   log('x = %s', x)
            #
            # Turns into
            # List<T> _for_yield_acc3;
            # my_generator(42, &_for_yield_acc3);
            # for (ListIter it(_for_yield_acc3) ...)

            self.yield_eager_for[o] = (eager_list_name, eager_list_type)

            self.yield_for_node = o  # ForStmt
            self.accept(iterated_over)
            self.yield_for_node = None

            self.write(';\n')

        else:  # assume it's like d.iteritems()?  Iterator type
            assert False, over_type

        if index0_name:
            # can't initialize two things in a for loop, so do it on a separate line
            self.write_ind('%s = 0;\n', index0_name)
            index_update = ', ++%s' % index0_name
        else:
            index_update = ''

        self.write_ind('for (%s it(', c_iter_type)
        if eager_list_name:
            self.write('&%s', eager_list_name)
        else:
            self.accept(iterated_over)  # the thing being iterated over
        self.write('); !it.Done(); it.Next()%s) {\n', index_update)

        # for x in it: ...
        # for i, x in enumerate(pairs): ...

        if isinstance(item_type, Instance) or index0_name:
            c_item_type = GetCType(item_type)
            self.write_ind('  %s ', c_item_type)
            self.accept(index_expr)
            if over_dict:
                self.write(' = it.Key();\n')
            else:
                self.write(' = it.Value();\n')

            # Register loop variable as a stack root.
            # Note we have mylib.Collect() in CommandEvaluator::_Execute(), and
            # it's called in a loop by _ExecuteList().  Although the 'child'
            # variable is already live by other means.
            # TODO: Test how much this affects performance.
            if CTypeIsManaged(c_item_type) and not self.stack_roots:
                self.write_ind('  StackRoot _for(&')
                self.accept(index_expr)
                self.write_ind(');\n')

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
                self.write_ind('  %s %s = it.Key();\n', key_type,
                               index_items[0].name)
                self.write_ind('  %s %s = it.Value();\n', val_type,
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
                    self.write_ind('  %s %s = it.Value();\n', c_item_type,
                                   temp_name)

                    self.indent += 1

                    # loop - for x, y in other:
                    self._WriteTupleUnpackingInLoop(temp_name, o.index.items,
                                                    item_type.items)

                    self.indent -= 1
                else:
                    self.write_ind('  %s %s = it.Value();\n', c_item_type,
                                   o.index.name)
                    #self.write_ind('  StackRoots _for(&%s)\n;', o.index.name)

        else:
            raise AssertionError('Unexpected type %s' % item_type)

        # Copy of visit_block, without opening {
        self.indent += 1
        block = o.body
        self._WriteBody(block.body)
        self.indent -= 1
        self.write_ind('}\n')

        if o.else_body:
            raise AssertionError("can't translate for-else")

    def _WriteCases(self, switch_expr: Expression, cases: util.CaseList,
                    default_block: Union['mypy.nodes.Block', int]) -> None:
        """ Write a list of (expr, block) pairs """

        for expr, body in cases:
            assert expr is not None, expr
            if not isinstance(expr, CallExpr):
                self.report_error(expr,
                                  'Expected call like case(x), got %s' % expr)
                return

            for i, arg in enumerate(expr.args):
                if i != 0:
                    self.write('\n')
                self.write_ind('case ')
                self.accept(arg)
                self.write(': ')

            self.accept(body)
            self.write_ind('  break;\n')

        if default_block == -1:
            # an error occurred
            return
        if default_block == -2:
            # This is too restrictive
            #self.report_error(switch_expr,
            #                  'switch got no else: for default block')
            return

        # Narrow the type
        assert not isinstance(default_block, int), default_block

        self.write_ind('default: ')
        self.accept(default_block)
        # don't write 'break'

    def _WriteSwitch(self, expr: Expression, o: 'mypy.nodes.WithStmt') -> None:
        """Write a switch statement over integers."""
        assert len(expr.args) == 1, expr.args

        self.write_ind('switch (')
        self.accept(expr.args[0])
        self.write(') {\n')

        assert len(o.body.body) == 1, o.body.body
        if_node = o.body.body[0]
        assert isinstance(if_node, IfStmt), if_node

        self.indent += 1
        cases: util.CaseList = []
        default_block = util._collect_cases(self.module_path,
                                            if_node,
                                            cases,
                                            errors=self.errors_keep_going)
        self._WriteCases(expr, cases, default_block)

        self.indent -= 1
        self.write_ind('}\n')

    def _WriteTagSwitch(self, expr: Expression,
                        o: 'mypy.nodes.WithStmt') -> None:
        """Write a switch statement over ASDL types."""
        assert len(expr.args) == 1, expr.args

        self.write_ind('switch (')
        self.accept(expr.args[0])
        self.write('->tag()) {\n')

        assert len(o.body.body) == 1, o.body.body
        if_node = o.body.body[0]
        assert isinstance(if_node, IfStmt), if_node

        self.indent += 1
        cases: util.CaseList = []
        default_block = util._collect_cases(self.module_path,
                                            if_node,
                                            cases,
                                            errors=self.errors_keep_going)
        self._WriteCases(expr, cases, default_block)

        self.indent -= 1
        self.write_ind('}\n')

    def _str_switch_cases(self, cases: util.CaseList) -> Any:
        cases2: List[Tuple[int, str, 'mypy.nodes.Block']] = []
        for expr, body in cases:
            if not isinstance(expr, CallExpr):
                # non-fatal check from _collect_cases
                break

            args = expr.args
            if len(args) != 1:
                self.report_error(
                    expr,
                    'str_switch can only have case("x"), not case("x", "y"): got %r'
                    % args)
                break

            if not isinstance(args[0], StrExpr):
                self.report_error(
                    expr,
                    'str_switch can only be used with constant strings, got %s'
                    % args[0])
                break

            s = args[0].value
            cases2.append((len(s), s, body))

        # Sort by string length
        cases2.sort(key=lambda pair: pair[0])
        grouped = itertools.groupby(cases2, key=lambda pair: pair[0])
        return grouped

    def _WriteStrSwitch(self, expr: Expression,
                        o: 'mypy.nodes.WithStmt') -> None:
        """Write a switch statement over strings."""
        assert len(expr.args) == 1, expr.args

        switch_expr = expr  # for later error

        switch_var = expr.args[0]
        if not isinstance(switch_var, NameExpr):
            self.report_error(
                expr.args[0],
                'str_switch(x) accepts only a variable name, got %s' %
                switch_var)
            return

        self.write_ind('switch (len(%s)) {\n' % switch_var.name)

        # There can only be one thing under 'with str_switch'
        assert len(o.body.body) == 1, o.body.body
        if_node = o.body.body[0]
        assert isinstance(if_node, IfStmt), if_node

        self.indent += 1

        cases: util.CaseList = []
        default_block = util._collect_cases(self.module_path,
                                            if_node,
                                            cases,
                                            errors=self.errors_keep_going)

        grouped_cases = self._str_switch_cases(cases)
        # Warning: this consumes internal iterator
        #self.log('grouped %s', list(grouped_cases))

        for str_len, group in grouped_cases:
            self.write_ind('case %s: {\n' % str_len)
            if_num = 0
            for _, case_str, block in group:
                self.indent += 1

                else_str = '' if if_num == 0 else 'else '
                self.write_ind('%sif (str_equals_c(%s, %s, %d)) ' %
                               (else_str, switch_var.name,
                                PythonStringLiteral(case_str), str_len))
                self.accept(block)

                self.indent -= 1
                if_num += 1

            self.indent += 1
            self.write_ind('else {\n')
            self.write_ind('  goto str_switch_default;\n')
            self.write_ind('}\n')
            self.indent -= 1

            self.write_ind('}\n')
            self.write_ind('  break;\n')

        if default_block == -1:
            # an error occurred
            return
        if default_block == -2:
            self.report_error(switch_expr,
                              'str_switch got no else: for default block')
            return

        # Narrow the type
        assert not isinstance(default_block, int), default_block

        self.write('\n')
        self.write_ind('str_switch_default:\n')
        self.write_ind('default: ')
        self.accept(default_block)

        self.indent -= 1
        self.write_ind('}\n')

    def visit_with_stmt(self, o: 'mypy.nodes.WithStmt') -> None:
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
            self._WriteSwitch(expr, o)
        elif callee_name == 'str_switch':
            self._WriteStrSwitch(expr, o)
        elif callee_name == 'tagswitch':
            self._WriteTagSwitch(expr, o)
        else:
            assert isinstance(expr, CallExpr), expr
            self.write_ind('{  // with\n')
            self.indent += 1

            self.write_ind('')
            self.accept(expr.callee)

            # FIX: Use braced initialization to avoid most-vexing parse when
            # there are 0 args!
            self.write(' ctx{')
            for i, arg in enumerate(expr.args):
                if i != 0:
                    self.write(', ')
                self.accept(arg)
            self.write('};\n\n')

            self._WriteBody(o.body.body)

            self.indent -= 1
            self.write_ind('}\n')

    def visit_del_stmt(self, o: 'mypy.nodes.DelStmt') -> None:

        d = o.expr
        if isinstance(d, IndexExpr):
            self.write_ind('')
            self.accept(d.base)

            if isinstance(d.index, SliceExpr):
                # del mylist[:] -> mylist->clear()

                sl = d.index
                assert sl.begin_index is None, sl
                assert sl.end_index is None, sl
                self.write('->clear()')
            else:
                # del mydict[mykey] raises KeyError, which we don't want
                raise AssertionError(
                    'Use mylib.dict_erase(d, key) instead of del d[key]')

            self.write(';\n')

    def oils_visit_constructor(self, o: ClassDef, stmt: FuncDef,
                               base_class_name: util.SymbolPath) -> None:
        self.write('\n')
        self.write('%s::%s(', o.name, o.name)
        self._WriteFuncParams(stmt, write_defaults=False)
        self.write(')')

        first_index = 0

        # Skip docstring
        maybe_skip_stmt = stmt.body.body[0]
        if (isinstance(maybe_skip_stmt, ExpressionStmt) and
                isinstance(maybe_skip_stmt.expr, StrExpr)):
            first_index += 1

        # Check for Base.__init__(self, ...) and move that to the initializer list.
        first_stmt = stmt.body.body[first_index]
        if (isinstance(first_stmt, ExpressionStmt) and
                isinstance(first_stmt.expr, CallExpr)):
            expr = first_stmt.expr
            #log('expr %s', expr)
            callee = first_stmt.expr.callee

            # TextOutput() : ColorOutput(f), ... {
            if (isinstance(callee, MemberExpr) and callee.name == '__init__'):
                base_constructor_args = expr.args
                #log('ARGS %s', base_constructor_args)
                self.write(' : %s(',
                           join_name(base_class_name, strip_package=True))
                for i, arg in enumerate(base_constructor_args):
                    if i == 0:
                        continue  # Skip 'this'
                    if i != 1:
                        self.write(', ')
                    self.accept(arg)
                self.write(')')

                first_index += 1

        self.write(' {\n')

        # Now visit the rest of the statements
        self.indent += 1

        if _IsContextManager(self.current_class_name):
            # For ctx_* classes only, do gHeap.PushRoot() for all the pointer
            # members
            member_vars = self.all_member_vars[o]
            for name in sorted(member_vars):
                _, c_type, is_managed = member_vars[name]
                if is_managed:
                    # VALIDATE_ROOTS doesn't complain even if it's not
                    # initialized?  Should be initialized after PushRoot().
                    #self.write_ind('this->%s = nullptr;\n' % name)
                    self.write_ind(
                        'gHeap.PushRoot(reinterpret_cast<RawObject**>(&(this->%s)));\n'
                        % name)

        for node in stmt.body.body[first_index:]:
            self.accept(node)
        self.indent -= 1
        self.write('}\n')

    def oils_visit_dunder_exit(self, o: ClassDef, stmt: FuncDef,
                               base_class_name: util.SymbolPath) -> None:
        self.write('\n')
        self.write_ind('%s::~%s()', o.name, o.name)

        self.write(' {\n')
        self.indent += 1

        # TODO:
        # - Can't throw exception in destructor.
        # - Check that you don't return early from destructor.  If so, we skip
        #   PopRoot(), which messes up the invariant!

        for node in stmt.body.body:
            self.accept(node)

        # For ctx_* classes only , gHeap.PopRoot() for all the pointer members
        if _IsContextManager(self.current_class_name):
            member_vars = self.all_member_vars[o]
            for name in sorted(member_vars):
                _, c_type, is_managed = member_vars[name]
                if is_managed:
                    self.write_ind('gHeap.PopRoot();\n')
        else:
            self.report_error(
                o, 'Any class with __exit__ should be named ctx_Foo (%s)' %
                (self.current_class_name, ))
            return

        self.indent -= 1
        self.write('}\n')

    def oils_visit_method(self, o: ClassDef, stmt: FuncDef,
                          base_class_name: util.SymbolPath) -> None:
        self.accept(stmt)

    # Module structure

    def visit_import(self, o: 'mypy.nodes.Import') -> None:
        pass

    def visit_import_from(self, o: 'mypy.nodes.ImportFrom') -> None:
        """
        Write C++ namespace aliases and 'using' for imports.
        We need them in the 'decl' phase for default arguments like
        runtime_asdl::scope_e -> scope_e
        """
        if o.id in ('__future__', 'typing'):
            return  # do nothing

        for name, alias in o.names:
            #self.log('ImportFrom id: %s name: %s alias: %s', o.id, name, alias)

            if name == 'log':  # varargs translation
                continue

            if o.id == 'mycpp.mylib':
                # These mylib functions are translated in a special way
                if name in ('switch', 'tagswitch', 'str_switch', 'iteritems',
                            'NewDict', 'probe'):
                    continue
                # STDIN_FILENO is #included
                if name == 'STDIN_FILENO':
                    continue

            # A heuristic that works for the Oils import style.
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
                #   write(), you end up 'using error::e_usage' in say
                #   'assign_osh', and it hasn't been defined yet.

                if alias:
                    # using runtime_asdl::emit_e = EMIT;
                    self.write_ind('using %s = %s::%s;\n', alias, last_dotted,
                                   name)
                else:
                    #    from _devbuild.gen.id_kind_asdl import Id
                    # -> using id_kind_asdl::Id.
                    using_str = 'using %s::%s;\n' % (last_dotted, name)
                    self.write_ind(using_str)

                    # Fully qualified:
                    # self.write_ind('using %s::%s;\n', '::'.join(dotted_parts), name)

            else:
                # If we're importing a module without an alias, we don't need to do
                # anything.  'namespace cmd_eval' is already defined.
                if not alias:
                    return

                #    from asdl import format as fmt
                # -> namespace fmt = format;
                self.write_ind('namespace %s = %s;\n', alias, name)

    # Statements

    def _WriteLocals(self, local_var_list: List[LocalVar]) -> None:
        # TODO: put the pointers first, and then register a single
        # StackRoots record.
        done = set()
        for lval_name, lval_type, is_param in local_var_list:
            c_type = GetCType(lval_type)
            if not is_param and lval_name not in done:
                if util.SMALL_STR and c_type == 'Str':
                    self.write_ind('%s %s(nullptr);\n', c_type, lval_name)
                else:
                    rhs = ' = nullptr' if CTypeIsManaged(c_type) else ''
                    self.write_ind('%s %s%s;\n', c_type, lval_name, rhs)

                    # TODO: we're not skipping the assignment, because of
                    # the RHS
                    if util.IsUnusedVar(lval_name):
                        # suppress C++ unused var compiler warnings!
                        self.write_ind('(void)%s;\n' % lval_name)

                done.add(lval_name)

        # Figure out if we have any roots to write with StackRoots
        roots = []  # keep it sorted
        full_func_name = None
        if self.current_func_node:
            full_func_name = split_py_name(self.current_func_node.fullname)

        for lval_name, lval_type, is_param in local_var_list:
            c_type = GetCType(lval_type)
            #self.log('%s %s %s', lval_name, c_type, is_param)
            if lval_name not in roots and CTypeIsManaged(c_type):
                if (not self.stack_roots or self.stack_roots.needs_root(
                        full_func_name, split_py_name(lval_name))):
                    roots.append(lval_name)

        #self.log('roots %s', roots)

        if len(roots):
            if (self.stack_roots_warn and len(roots) > self.stack_roots_warn):
                log('WARNING: %s() has %d stack roots. Consider refactoring this function.'
                    % (self.current_func_node.fullname, len(roots)))

            for i, r in enumerate(roots):
                self.write_ind('StackRoot _root%d(&%s);\n' % (i, r))

            self.write('\n')

    def visit_block(self, block: 'mypy.nodes.Block') -> None:
        self.write('{\n')  # not indented to use same line as while/if

        self.indent += 1
        self._WriteBody(block.body)
        self.indent -= 1

        self.write_ind('}\n')

    def oils_visit_expression_stmt(self,
                                   o: 'mypy.nodes.ExpressionStmt') -> None:
        self.write_ind('')
        self.accept(o.expr)
        self.write(';\n')

    def visit_operator_assignment_stmt(
            self, o: 'mypy.nodes.OperatorAssignmentStmt') -> None:
        self.write_ind('')
        self.accept(o.lvalue)
        self.write(' %s= ', o.op)  # + to +=
        self.accept(o.rvalue)
        self.write(';\n')

    def visit_while_stmt(self, o: 'mypy.nodes.WhileStmt') -> None:
        self.write_ind('while (')
        self.accept(o.expr)
        self.write(') ')
        self.accept(o.body)

    def visit_return_stmt(self, o: 'mypy.nodes.ReturnStmt') -> None:
        # Examples:
        # return
        # return None
        # return my_int + 3;
        self.write_ind('return ')
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
                    self.write('%s(' % c_ret_type)
                    for i, item in enumerate(o.expr.items):
                        if i != 0:
                            self.write(', ')
                        self.accept(item)
                    self.write(');\n')
                    return

            # Not returning tuple
            self.accept(o.expr)

        self.write(';\n')

    def visit_if_stmt(self, o: 'mypy.nodes.IfStmt') -> None:
        # Not sure why this wouldn't be true
        assert len(o.expr) == 1, o.expr

        condition = o.expr[0]

        if not _CheckCondition(condition, self.types):
            self.report_error(
                o,
                "Use explicit len(obj) or 'obj is not None' for mystr, mylist, mydict"
            )
            return

        if util.ShouldVisitIfExpr(o):
            self.write_ind('if (')
            for e in o.expr:
                self.accept(e)
            self.write(') ')

        if util.ShouldVisitIfBody(o):
            cond = util.GetSpecialIfCondition(o)
            if cond == 'CPP':
                self.write_ind('// if MYCPP\n')
                self.write_ind('')

            for body in o.body:
                self.accept(body)

            if cond == 'CPP':
                self.write_ind('// endif MYCPP\n')

        if util.ShouldVisitElseBody(o):
            cond = util.GetSpecialIfCondition(o)
            if cond == 'PYTHON':
                self.write_ind('// if not PYTHON\n')
                self.write_ind('')

            if util.ShouldVisitIfBody(o):
                self.write_ind('else ')

            self.accept(o.else_body)

            if cond == 'PYTHON':
                self.write_ind('// endif MYCPP\n')

    def visit_break_stmt(self, o: 'mypy.nodes.BreakStmt') -> None:
        self.write_ind('break;\n')

    def visit_continue_stmt(self, o: 'mypy.nodes.ContinueStmt') -> None:
        self.write_ind('continue;\n')

    def visit_pass_stmt(self, o: 'mypy.nodes.PassStmt') -> None:
        self.write_ind(';  // pass\n')

    def visit_raise_stmt(self, o: 'mypy.nodes.RaiseStmt') -> None:
        # C++ compiler is aware of assert(0) for unreachable code
        if o.expr and isinstance(o.expr, CallExpr):
            if o.expr.callee.name == 'AssertionError':
                self.write_ind('assert(0);  // AssertionError\n')
                return
            if o.expr.callee.name == 'NotImplementedError':
                self.write_ind(
                    'FAIL(kNotImplemented);  // Python NotImplementedError\n')
                return

        self.write_ind('throw ')
        # it could be raise -> throw ; .  OSH uses that.
        if o.expr:
            self.accept(o.expr)
        self.write(';\n')

    def visit_try_stmt(self, o: 'mypy.nodes.TryStmt') -> None:
        self.write_ind('try ')
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
                self.report_error(o, "try couldn't determine c_type")
                return

            if v:
                self.write_ind('catch (%s %s) ', c_type, v.name)
            else:
                self.write_ind('catch (%s) ', c_type)
            self.accept(handler)

            caught = True

        if not caught:
            self.report_error(o, 'try should have an except')

        if o.else_body:
            self.report_error(o, 'try/else not supported')

        if o.finally_body:
            self.report_error(o, 'try/finally not supported')
