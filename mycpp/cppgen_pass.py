"""
cppgen.py - AST pass to that prints C++ code
"""
import io
import json  # for "C escaping"
import os
import sys

from typing import overload, Union, Optional, Any, Dict

from mypy.visitor import ExpressionVisitor, StatementVisitor
from mypy.types import (
    Type, AnyType, NoneTyp, TupleType, Instance, Overloaded, CallableType,
    UnionType, UninhabitedType, PartialType, TypeAliasType)
from mypy.nodes import (
    Expression, Statement, Block, NameExpr, IndexExpr, MemberExpr, TupleExpr,
    ExpressionStmt, AssignmentStmt, IfStmt, StrExpr, SliceExpr, FuncDef,
    UnaryExpr, ComparisonExpr, CallExpr, IntExpr, ListExpr, DictExpr,
    ListComprehension)

from mycpp import format_strings
from mycpp.crash import catch_errors
from mycpp.util import log

from typing import Tuple


T = None

class UnsupportedException(Exception):
    pass


def _SkipAssignment(var_name):
  """Skip _ = log and unused = log"""
  return var_name == '_' or var_name.startswith('unused')


def _GetCTypeForCast(type_expr):
  if isinstance(type_expr, MemberExpr):
    subtype_name = '%s::%s' % (type_expr.expr.name, type_expr.name)
  elif isinstance(type_expr, IndexExpr):
    # List[word_t] would be a problem.
    # But worked around it in osh/word_parse.py
    #subtype_name = 'List<word_t>'
    raise AssertionError()
  else:
    subtype_name = type_expr.name

  # Hack for now
  if subtype_name != 'int':
    subtype_name += '*'
  return subtype_name


def _GetCastKind(module_path, subtype_name):
  cast_kind = 'static_cast'
  # Hack for the CastDummy in expr_to_ast.py
  if 'expr_to_ast.py' in module_path:
    for name in (
        'sh_array_literal', 'command_sub', 'braced_var_sub',
        'double_quoted', 'single_quoted',
        # Another kind of hack, not because of CastDummy
        'place_expr_t',
        ):
      if name in subtype_name:
        cast_kind = 'reinterpret_cast'
        break
  return cast_kind


def _GetContainsFunc(t):
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


def _CheckConditionType(t):
  """
  strings, lists, and dicts shouldn't be used in boolean contexts, because that
  doesn't translate to C++.
  """
  if isinstance(t, Instance):
    type_name = t.type.fullname
    if type_name == 'builtins.str':
      return False

    elif type_name == 'builtins.list':
      return False

    elif type_name == 'builtins.dict':
      return False

  elif isinstance(t, UnionType):
    if (len(t.items) == 2 and
        IsStr(t.items[0]) and isinstance(t.items[1], NoneTyp)):
      return False  # Optional[str]

  return True


def CTypeIsManaged(c_type):
  # type: (str) -> bool
  """For rooting and field masks."""
  assert c_type != 'void'

  # int, double, bool, scope_t enums, etc. are not managed
  return c_type.endswith('*')


def get_c_type(t, param=False, local=False):
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

    if type_name == 'builtins.int':
      c_type = 'int'

    elif type_name == 'builtins.float':
      c_type = 'double'

    elif type_name == 'builtins.bool':
      c_type = 'bool'

    elif type_name == 'builtins.str':
      c_type = 'Str'
      is_pointer = True

    elif type_name == 'builtins.list':
      assert len(t.args) == 1, t.args
      type_param = t.args[0]
      inner_c_type = get_c_type(type_param)
      c_type = 'List<%s>' % inner_c_type
      is_pointer = True

    elif type_name == 'builtins.dict':
      params = []
      for type_param in t.args:
        params.append(get_c_type(type_param))
      c_type = 'Dict<%s>' % ', '.join(params)
      is_pointer = True

    elif type_name == 'typing.IO':
      c_type = 'void'
      is_pointer = True

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
      inner_c_types.append(get_c_type(inner_type))

    c_type = 'Tuple%d<%s>' % (len(t.items), ', '.join(inner_c_types))
    is_pointer = True

  elif isinstance(t, UnionType):
    # Special case for Optional[T] == Union[T, None]
    if len(t.items) != 2:
      raise NotImplementedError('Expected Optional, got %s' % t)

    if not isinstance(t.items[1], NoneTyp):
      raise NotImplementedError('Expected Optional, got %s' % t)

    c_type = get_c_type(t.items[0])

  elif isinstance(t, CallableType):
    # Function types are expanded
    # Callable[[Parser, Token, int], arith_expr_t] =>
    # arith_expr_t* (*f)(Parser*, Token*, int) nud;

    ret_type = get_c_type(t.ret_type)
    arg_types = [get_c_type(typ) for typ in t.arg_types]
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
    return get_c_type(t.alias.target)

  else:
    raise NotImplementedError('MyPy type: %s %s' % (type(t), t))

  if is_pointer:
    if param or local:
      c_type = 'Local<%s>' % c_type
    else:
      c_type += '*'

  return c_type


def get_c_return_type(t) -> Tuple[str, bool]:
  """
  Returns a C string, and whether the tuple-by-value optimization was applied
  """

  c_ret_type = get_c_type(t)

  # Optimization: Return tupels BY VALUE
  if isinstance(t, TupleType):
    assert c_ret_type.endswith('*')
    return c_ret_type[:-1], True
  else:
    return c_ret_type, False


class Generate(ExpressionVisitor[T], StatementVisitor[None]):

    def __init__(self, types: Dict[Expression, Type], const_lookup, f,
                 virtual=None, local_vars=None, fmt_ids=None,
                 mask_funcs=None,
                 decl=False, forward_decl=False, ret_val_rooting=False):
      self.types = types
      self.const_lookup = const_lookup
      self.f = f 

      self.virtual = virtual
      # local_vars: FuncDef node -> list of type, var
      # This is different from member_vars because we collect it in the 'decl'
      # phase.  But then write it in the definition phase.
      self.local_vars = local_vars
      self.fmt_ids = fmt_ids
      self.mask_funcs = mask_funcs
      self.fmt_funcs = io.StringIO()

      self.decl = decl
      self.forward_decl = forward_decl
      self.ret_val_rooting = ret_val_rooting

      self.unique_id = 0

      self.indent = 0
      self.local_var_list = []  # Collected at assignment
      self.prepend_to_block = None  # For writing vars after {
      self.current_func_node = None

      # This is cleared when we start visiting a class.  Then we visit all the
      # methods, and accumulate the types of everything that looks like
      # self.foo = 1.  Then we write C++ class member declarations at the end
      # of the class.
      # This is all in the 'decl' phase.
      self.member_vars = {}  # type: Dict[str, Type]

      self.current_class_name = None  # for prototypes
      self.current_method_name = None

      self.imported_names = set()  # For module::Foo() vs. self.foo

    def log(self, msg, *args):
      ind_str = self.indent * '  '
      log(ind_str + msg, *args)

    def write(self, msg, *args):
      if self.decl or self.forward_decl:
        return
      if args:
        msg = msg % args
      self.f.write(msg)

    # Write respecting indent
    def write_ind(self, msg, *args):
      if self.decl or self.forward_decl:
        return
      ind_str = self.indent * '  '
      if args:
        msg = msg % args
      self.f.write(ind_str + msg)

    # A little hack to reuse this pass for declarations too
    def decl_write(self, msg, *args):
      # TODO:
      # self.header_f ?
      # Just one file for all exported?

      if args:
        msg = msg % args
      self.f.write(msg)

    def decl_write_ind(self, msg, *args):
      ind_str = self.indent * '  '
      if args:
        msg = msg % args
      self.f.write(ind_str + msg)


    #
    # COPIED from IRBuilder
    #

    @overload
    def accept(self, node: Expression) -> T: ...

    @overload
    def accept(self, node: Statement) -> None: ...

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

    # Not in superclasses:

    def visit_mypy_file(self, o: 'mypy.nodes.MypyFile') -> T:
        # Skip some stdlib stuff.  A lot of it is brought in by 'import
        # typing'.
        if o.fullname in (
            '__future__', 'sys', 'types', 'typing', 'abc', '_ast', 'ast',
            '_weakrefset', 'collections', 'cStringIO', 're', 'builtins'):

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

        self.decl_write_ind('namespace %s {  // %s\n', mod_parts[-1], comment)
        self.decl_write('\n')

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
          self.decl_write('\n')
          self.decl_write(self.fmt_funcs.getvalue())
          self.fmt_funcs = io.StringIO()  # clear it for the next file

        if self.forward_decl:
          self.indent -= 1

        self.decl_write('\n')
        self.decl_write_ind(
            '}  // %s namespace %s\n', comment, mod_parts[-1])
        self.decl_write('\n')


    # NOTE: Copied ExpressionVisitor and StatementVisitor nodes below!

    # LITERALS

    def visit_int_expr(self, o: 'mypy.nodes.IntExpr') -> T:
        self.write(str(o.value))

    def visit_str_expr(self, o: 'mypy.nodes.StrExpr') -> T:
        self.write(self.const_lookup[o])

    def visit_bytes_expr(self, o: 'mypy.nodes.BytesExpr') -> T:
        pass

    def visit_unicode_expr(self, o: 'mypy.nodes.UnicodeExpr') -> T:
        pass

    def visit_float_expr(self, o: 'mypy.nodes.FloatExpr') -> T:
        # e.g. for arg.t > 0.0
        self.write(str(o.value))

    def visit_complex_expr(self, o: 'mypy.nodes.ComplexExpr') -> T:
        pass

    # Expressions

    def visit_ellipsis(self, o: 'mypy.nodes.EllipsisExpr') -> T:
        pass

    def visit_star_expr(self, o: 'mypy.nodes.StarExpr') -> T:
        pass

    def visit_name_expr(self, o: 'mypy.nodes.NameExpr') -> T:
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

    def visit_member_expr(self, o: 'mypy.nodes.MemberExpr') -> T:
        t = self.types[o]
        if o.expr:  
          #log('member o = %s', o)

          # This is an approximate hack that assumes that locals don't shadow
          # imported names.  Might be a problem with names like 'word'?
          if (isinstance(o.expr, NameExpr) and (
              o.expr.name in self.imported_names or
              o.expr.name in ('mylib', 'libc', 'posix', 'fcntl_',
                              'time_', 'termios', 'signal_') or
              o.name == '__init__'
              )):
            op = '::'
          else:
            op = '->'  # Everything is a pointer

          self.accept(o.expr)
          self.write(op)

        if o.name == 'errno':
          # Avoid conflict with errno macro
          # e->errno turns into e->errno_
          self.write('errno_')
        else:
          self.write('%s', o.name)

    def visit_yield_from_expr(self, o: 'mypy.nodes.YieldFromExpr') -> T:
        pass

    def visit_yield_expr(self, o: 'mypy.nodes.YieldExpr') -> T:
        pass

    def _WriteArgList(self, o):
      self.write('(')
      # So we can get better AssertionError messages in Python
      if o.callee.name != 'AssertionError':
        for i, arg in enumerate(o.args):
          if i != 0:
            self.write(', ')
          self.accept(arg)
      self.write(')')

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
        # TODO: rename int_to_str?  or Str::from_int()?
        if (callee_name not in ('str', 'bool', 'float') and
            isinstance(ret_type, Instance)):

          ret_type_name = ret_type.type.name

          # HACK: Const is the callee; expr__Const is the return type
          if (ret_type_name == callee_name or
              ret_type_name.endswith('__' + callee_name)):
            return True

      return False

    def visit_call_expr(self, o: 'mypy.nodes.CallExpr') -> T:
        if o.callee.name == 'isinstance':
          assert len(o.args) == 2, args
          obj = o.args[0]
          typ = o.args[1]

          if 0:
            log('obj %s', obj)
            log('typ %s', typ)

          self.accept(obj)
          self.write('->tag_() == ')
          assert isinstance(typ, NameExpr), typ

          # source__CFlag -> source_e::CFlag
          tag = typ.name.replace('__', '_e::')
          self.write(tag)
          return

        #    return cast(sh_array_literal, tok)
        # -> return static_cast<sh_array_literal*>(tok)

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

        # Translate printf-style vargs for some functions, e.g.
        #
        # p_die('foo %s', x, token=t)
        #   =>
        # p_die(fmt1(x), t)
        #
        # And then we need 3 or 4 version of p_die()?  For the rest of the
        # tokens.

        # Others:
        # - debug_f.log()?
        # Maybe I should rename them all printf()
        # or fprintf()?  Except p_die() has extra args

        if o.callee.name == 'log' or o.callee.name == 'stderr_line':
          args = o.args
          if len(args) == 1:  # log(CONST)
            self.write('println_stderr(')
            self.accept(args[0])
            self.write(')')
            return

          rest = args[1:]
          if self.decl:
            fmt = args[0].value
            fmt_types = [self.types[arg] for arg in rest]
            temp_name = self._WriteFmtFunc(fmt, fmt_types)
            self.fmt_ids[o] = temp_name

          # DEFINITION PASS: Write the call
          self.write('println_stderr(%s(' % self.fmt_ids[o])
          for i, arg in enumerate(rest):
            if i != 0:
              self.write(', ')
            self.accept(arg)
          self.write('))')
          return

        # TODO: Consolidate X_die() and log()?  It has an extra arg though.
        if o.callee.name in ('p_die', 'e_die', 'e_strict', 'e_usage'):
          args = o.args
          if len(args) == 1:  # log(CONST)
            self.write('%s(' % o.callee.name)
            self.accept(args[0])
            self.write(')')
            return

          has_keyword_arg = o.arg_names[-1] is not None
          if has_keyword_arg:
            rest = args[1:-1]
          else:
            rest = args[1:]

          # If there are no arguments, it must look like
          # Same with
          # e_die('constant string')
          if not rest:
            pass

          if self.decl:
            fmt_arg = args[0]
            if isinstance(fmt_arg, StrExpr):
              fmt_types = [self.types[arg] for arg in rest]
              temp_name = self._WriteFmtFunc(fmt_arg.value, fmt_types)
              self.fmt_ids[o] = temp_name
            else:
              # oil_lang/expr_to_ast.py uses RANGE_POINT_TOO_LONG, etc.
              self.fmt_ids[o] = "dynamic_fmt_dummy"

          # Should p_die() be in mylib?
          # DEFINITION PASS: Write the call
          self.write('%s(%s(' % (o.callee.name, self.fmt_ids[o]))
          for i, arg in enumerate(rest):
            if i != 0:
              self.write(', ')
            self.accept(arg)

          if has_keyword_arg:
            self.write('), ')
            self.accept(args[-1])
          else:
            self.write(')')

          self.write(')')

          return

        callee_name = o.callee.name

        if self._IsInstantiation(o):
          self.write('Alloc<')
          self.accept(o.callee)
          self.write('>')
          self._WriteArgList(o)
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

        self._WriteArgList(o)

        # TODO: look at keyword arguments!
        #self.log('  arg_kinds %s', o.arg_kinds)
        #self.log('  arg_names %s', o.arg_names)

    def _WriteFmtFunc(self, fmt, fmt_types):
      """Append a fmtX() function to a buffer.

      Returns:
        the temp fmtX() name we used.
      """
      temp_name = 'fmt%d' % self.fmt_ids['_counter']
      self.fmt_ids['_counter'] += 1

      fmt_parts = format_strings.Parse(fmt)
      self.fmt_funcs.write('inline Str* %s(' % temp_name)

      # NOTE: We're not calling Alloc<> inside these functions, so
      # they don't need StackRoots?
      for i, typ in enumerate(fmt_types):
        if i != 0:
          self.fmt_funcs.write(', ');
        self.fmt_funcs.write('%s a%d' % (get_c_type(typ), i))

      self.fmt_funcs.write(') {\n')
      self.fmt_funcs.write('  gBuf.reset();\n')

      for part in fmt_parts:
        if isinstance(part, format_strings.LiteralPart):
          # MyPy does bad escaping.
          # NOTE: We could do this in the CALLER to _WriteFmtFunc?

          byte_string = bytes(part.s, 'utf-8')

          # In Python 3
          # >>> b'\\t'.decode('unicode_escape')
          # '\t'

          raw_string = format_strings.DecodeMyPyString(part.s)
          n = len(raw_string)  # NOT using part.strlen

          escaped = json.dumps(raw_string)
          self.fmt_funcs.write(
              '  gBuf.write_const(%s, %d);\n' % (escaped, n))
        elif isinstance(part, format_strings.SubstPart):
          # TODO: respect part.width as rjust()
          self.fmt_funcs.write(
              '  gBuf.format_%s(a%d);\n' %
              (part.char_code, part.arg_num))
        else:
          raise AssertionError(part)

      self.fmt_funcs.write('  return gBuf.getvalue();\n')
      self.fmt_funcs.write('}\n')
      self.fmt_funcs.write('\n')

      return temp_name

    def visit_op_expr(self, o: 'mypy.nodes.OpExpr') -> T:
        c_op = o.op

        # a + b when a and b are strings.  (Can't use operator overloading
        # because they're pointers.)
        left_type = self.types[o.left]
        right_type = self.types[o.right]

        # NOTE: Need get_c_type to handle Optional[Str*] in ASDL schemas.
        # Could tighten it up later.
        left_ctype = get_c_type(left_type)
        right_ctype = get_c_type(right_type)

        #if c_op == '+':
        if 0:
          self.log('*** %r', c_op)
          self.log('%s', o.left)
          self.log('%s', o.right)
          #self.log('t0 %r', t0.type.fullname)
          #self.log('t1 %r', t1.type.fullname)
          self.log('left_ctype %r', left_ctype)
          self.log('right_ctype %r', right_ctype)
          self.log('')

        if left_ctype == right_ctype == 'Str*' and c_op == '+':
          self.write('str_concat(')
          self.accept(o.left)
          self.write(', ')
          self.accept(o.right)
          self.write(')')
          return

        if left_ctype == 'Str*' and right_ctype == 'int' and c_op == '*':
          self.write('str_repeat(')
          self.accept(o.left)
          self.write(', ')
          self.accept(o.right)
          self.write(')')
          return

        # [None] * 3  =>  list_repeat(None, 3)
        if left_ctype.startswith('List<') and right_ctype == 'int' and c_op == '*':
          self.write('list_repeat(')
          self.accept(o.left.items[0])
          self.write(', ')
          self.accept(o.right)
          self.write(')')
          return

        # RHS can be primitive or tuple
        if left_ctype == 'Str*' and c_op == '%':
          if not isinstance(o.left, StrExpr):
            raise AssertionError('Expected constant format string, got %s' % o.left)
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

          # Write a buffer with fmtX() functions.
          if self.decl:
            fmt = o.left.value

            # TODO: I want to do this later
            temp_name = self._WriteFmtFunc(fmt, fmt_types)
            self.fmt_ids[o] = temp_name

          # In the definition pass, write the call site.
          self.write('%s(' % self.fmt_ids[o])
          if isinstance(right_type, TupleType):
            for i, item in enumerate(o.right.items):
              if i != 0:
                self.write(', ')
              self.accept(item)
          else:  # '[%s]' % x
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
          self.write(' == ')
          self.accept(o.operands[1])
          return

        if operator == 'is not':  # foo is not None => foo != nullptr
          self.accept(o.operands[0])
          self.write(' != ')
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
            self.write('!(')

          # NOTE: This could also be str_equals(left, right)?  Does it make a
          # difference?
          if left_type > 1 or right_type > 1:
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
        contains_func = _GetContainsFunc(t1)

        if operator == 'in':
          if isinstance(right, TupleExpr):
            left_type = self.types[left]

            equals_func = None
            if IsStr(left_type):
              equals_func = 'str_equals'
            elif (isinstance(left_type, UnionType) and len(left_type.items) == 2 and
                  IsStr(left_type.items[0]) and isinstance(left_type.items[1], NoneTyp)):
              equals_func = 'maybe_str_equals'

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
            # x not in (1, 2, 3) => (x != 1 && x != 2 && x != 3)
            self.write('(')

            for i, item in enumerate(right.items):
              if i != 0:
                self.write(' && ')
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
        self.write(op_str)
        self.accept(o.expr)

    def _WriteListElements(self, o, sep=', '):
        # sep may be 'COMMA' for a macro
        self.write('{')
        for i, item in enumerate(o.items):
            if i != 0:
                self.write(sep)
            self.accept(item)
        self.write('}')

    def visit_list_expr(self, o: 'mypy.nodes.ListExpr') -> T:
        list_type = self.types[o]
        #self.log('**** list_type = %s', list_type)
        c_type = get_c_type(list_type)

        item_type = list_type.args[0]  # int for List[int]
        item_c_type = get_c_type(item_type)

        assert c_type.endswith('*'), c_type
        c_type = c_type[:-1]  # HACK TO CLEAN UP

        if len(o.items) == 0:
            self.write('Alloc<%s>()' % c_type)
        else:
            self.write('NewList<%s>(std::initializer_list<%s>' %
                       (item_c_type, item_c_type))
            self._WriteListElements(o)
            self.write(')')

    def _WriteDictElements(self, o, key_type, val_type):
        # Ran into a limit of C++ type inference.  Somehow you need
        # std::initializer_list{} here, not just {}
        self.write('std::initializer_list<%s>{' % get_c_type(key_type))
        for i, item in enumerate(o.items):
          pass
        self.write('}, ')

        self.write('std::initializer_list<%s>{' % get_c_type(val_type))
        # TODO: values
        self.write('}')

    def visit_dict_expr(self, o: 'mypy.nodes.DictExpr') -> T:
        dict_type = self.types[o]
        key_type = dict_type.args[0]
        val_type = dict_type.args[1]

        c_type = get_c_type(dict_type)
        assert c_type.endswith('*'), c_type
        c_type = c_type[:-1]  # HACK TO CLEAN UP

        self.write('Alloc<%s>(' % c_type)
        if o.items:
          self._WriteDictElements(o, key_type, val_type)
        self.write(')')

    def visit_tuple_expr(self, o: 'mypy.nodes.TupleExpr') -> T:
        tuple_type = self.types[o]
        c_type = get_c_type(tuple_type)
        assert c_type.endswith('*'), c_type
        c_type = c_type[:-1]  # HACK TO CLEAN UP

        self.write('(Alloc<%s>(' % c_type)
        for i, item in enumerate(o.items):
          if i != 0:
            self.write(', ')
          self.accept(item)
        self.write('))')

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
          self.write('->index_(')
          self.accept(o.index)
          self.write(')')

    def visit_type_application(self, o: 'mypy.nodes.TypeApplication') -> T:
        pass

    def visit_lambda_expr(self, o: 'mypy.nodes.LambdaExpr') -> T:
        pass

    def visit_list_comprehension(self, o: 'mypy.nodes.ListComprehension') -> T:
        pass

    def visit_set_comprehension(self, o: 'mypy.nodes.SetComprehension') -> T:
        pass

    def visit_dictionary_comprehension(self, o: 'mypy.nodes.DictionaryComprehension') -> T:
        pass

    def visit_generator_expr(self, o: 'mypy.nodes.GeneratorExpr') -> T:
        pass

    def visit_slice_expr(self, o: 'mypy.nodes.SliceExpr') -> T:
        self.write('->slice(')
        if o.begin_index:
          self.accept(o.begin_index)
        else: 
          self.write('0')  # implicit begining

        if o.end_index:
          self.write(', ')
          self.accept(o.end_index)
        self.write(')')

        if o.stride:
          raise AssertionError('Stride not supported')

    def visit_conditional_expr(self, o: 'mypy.nodes.ConditionalExpr') -> T:
        cond_type = self.types[o.cond]

        if not _CheckConditionType(cond_type):
          raise AssertionError(
              "Can't use str, list, or dict in boolean context")

        # 0 if b else 1 -> b ? 0 : 1
        self.accept(o.cond)
        self.write(' ? ')
        self.accept(o.if_expr)
        self.write(' : ')
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

    def _write_tuple_unpacking(self, temp_name, lval_items, item_types,
                               is_return=False):
      """Used by assignment and for loops."""
      for i, (lval_item, item_type) in enumerate(zip(lval_items, item_types)):
        #self.log('*** %s :: %s', lval_item, item_type)
        if isinstance(lval_item, NameExpr):
          if _SkipAssignment(lval_item.name):
            continue

          item_c_type = get_c_type(item_type)
          # declare it at the top of the function
          if self.decl:
            self.local_var_list.append((lval_item.name, item_c_type))
          self.write_ind('%s', lval_item.name)
        else:
          # Could be MemberExpr like self.foo, self.bar = baz
          self.write_ind('')
          self.accept(lval_item)

        # Tuples that are return values aren't pointers
        op = '.' if is_return else '->'
        self.write(' = %s%sat%d();\n', temp_name, op, i)  # RHS

    def visit_assignment_stmt(self, o: 'mypy.nodes.AssignmentStmt') -> T:
        # Declare constant strings.  They have to be at the top level.
        if self.decl and self.indent == 0 and len(o.lvalues) == 1:
          lval = o.lvalues[0]
          c_type = get_c_type(self.types[lval])
          if not _SkipAssignment(lval.name):
            self.decl_write('extern %s %s;\n', c_type, lval.name)

        # I think there are more than one when you do a = b = 1, which I never
        # use.
        assert len(o.lvalues) == 1, o.lvalues
        lval = o.lvalues[0]

        # Special case for global constants.  L = [1, 2] or D = {}
        #
        # We avoid Alloc<T>, since that can't be done until main().
        #
        # It would be nice to make these completely constexpr, e.g.
        # initializing Slab<T> with the right layout from initializer_list, but
        # it isn't easy.  Would we need a constexpr hash?
        #
        # Limitation: This doesn't handle a = f([1, 2]), but we don't use that
        # in Oil.

        if self.indent == 0:
          assert isinstance(lval, NameExpr), lval
          if _SkipAssignment(lval.name):
            return

          #self.log('    GLOBAL List/Dict: %s', lval.name)

          lval_type = self.types[lval]

          if isinstance(o.rvalue, ListExpr):
            item_type = lval_type.args[0]
            item_c_type = get_c_type(item_type)

            # Then a pointer to it
            self.write('GLOBAL_LIST(%s, %d, %s, ',
                item_c_type, len(o.rvalue.items), lval.name)

            # TODO: Assert that every item is a constant?
            # COMMA for macro
            self._WriteListElements(o.rvalue, sep=' COMMA ')

            self.write(');\n')
            return

          # d = {} at the TOP LEVEL
          # TODO: Change this to
          # - GLOBAL_DICT(name, int, {42, 0}, Str, {str1, str2})
          # So it has Tag::Global

          if isinstance(o.rvalue, DictExpr):
            key_type, val_type = lval_type.args

            key_c_type = get_c_type(key_type)
            val_c_type = get_c_type(val_type)

            temp_name = 'gdict%d' % self.unique_id
            self.unique_id += 1

            # Value
            self.write('Dict<%s, %s> %s(', key_c_type, val_c_type, temp_name)
            self._WriteDictElements(o.rvalue, key_type, val_type)
            self.write(');\n')

            # Then a pointer to it
            self.write('Dict<%s, %s>* %s = &%s;\n', key_c_type, val_c_type,
                lval.name, temp_name)
            return

          # TODO: Change this to
          # - GLOBAL_INSTANCE(name, Token, ...)
          # for Tag::Global
          if isinstance(o.rvalue, CallExpr):
            call_expr = o.rvalue
            if self._IsInstantiation(call_expr):
              temp_name = 'gobj%d' % self.unique_id
              self.unique_id += 1

              #self.log('INSTANCE lval %s rval %s', lval, call_expr)

              self.write('\n')
              self.write('%s %s', call_expr.callee.name, temp_name)
              # C c;, not C c(); which is most vexing parse
              if call_expr.args:
                self._WriteArgList(call_expr)
              self.write(';\n')
              self.write('%s %s = &%s;', get_c_type(lval_type), lval.name,
                  temp_name)
              self.write('\n')
              return

        #
        # Non-top-level
        #

        if isinstance(o.rvalue, CallExpr):
          #    d = NewDict()  # type: Dict[int, int]
          # -> auto* d = NewDict<int, int>();
          if o.rvalue.callee.name == 'NewDict':

            lval_type = self.types[lval]

            key_type, val_type = lval_type.args

            key_c_type = get_c_type(key_type)
            val_c_type = get_c_type(val_type)

            self.write_ind('auto* %s = NewDict<%s, %s>();\n',
                           lval.name, key_c_type, val_c_type)
            # Doesn't take elememnts
            #self._WriteDictElements(o.rvalue, key_type, val_type)
            #self.write(');\n')
            return

          #    src = cast(source__SourcedFile, src)
          # -> source__SourcedFile* src = static_cast<source__SourcedFile>(src)
          if o.rvalue.callee.name == 'cast':
            assert isinstance(lval, NameExpr)
            call = o.rvalue
            type_expr = call.args[0]
            subtype_name = _GetCTypeForCast(type_expr)

            cast_kind = _GetCastKind(self.module_path, subtype_name)

            # HACK: Distinguish between UP cast and DOWN cast.
            # osh/cmd_parse.py _MakeAssignPair does an UP cast within branches.
            # _t is the base type, so that means it's an upcast.
            if isinstance(type_expr, NameExpr) and type_expr.name.endswith('_t'):
              if self.decl:
                self.local_var_list.append((lval.name, subtype_name))
              self.write_ind(
                  '%s = %s<%s>(', lval.name, cast_kind, subtype_name)
            else:
              self.write_ind(
                  '%s %s = %s<%s>(', subtype_name, lval.name, cast_kind,
                  subtype_name)

            self.accept(call.args[1])  # variable being casted
            self.write(');\n')
            return

        if isinstance(lval, NameExpr):
          if _SkipAssignment(lval.name):
            return

          lval_type = self.types[lval]
          #c_type = get_c_type(lval_type, local=self.indent != 0)
          c_type = get_c_type(lval_type)

          # for "hoisting" to the top of the function
          if self.current_func_node:
            self.write_ind('%s = ', lval.name)
            if self.decl:
              self.local_var_list.append((lval.name, c_type))
          else:
            # globals always get a type -- they're not mutated
            self.write_ind('%s %s = ', c_type, lval.name)

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
            self.write('Alloc<%s>();\n' % c_type[:-1])

            over_type = self.types[seq]
            #self.log('  iterating over type %s', over_type)

            if over_type.type.fullname == 'builtins.list':
              c_type = get_c_type(over_type)
              assert c_type.endswith('*'), c_type
              c_iter_type = c_type.replace('List', 'ListIter', 1)[:-1]  # remove *
            else:
              # Example: assoc == Optional[Dict[str, str]] 
              c_iter_type = 'TODO_ASSOC'

            self.write_ind('for (%s it(', c_iter_type)
            self.accept(seq)
            self.write('); !it.Done(); it.Next()) {\n')

            seq_type = self.types[seq]
            item_type = seq_type.args[0]  # get 'int' from 'List<int>'

            if isinstance(item_type, Instance):
              self.write_ind('  %s ', get_c_type(item_type))
              # TODO(StackRoots): for ch in 'abc'
              self.accept(index_expr)
              self.write(' = it.Value();\n')
            
            elif isinstance(item_type, TupleType):  # for x, y in pairs
              c_item_type = get_c_type(item_type)

              if isinstance(index_expr, TupleExpr):
                temp_name = 'tup%d' % self.unique_id
                self.unique_id += 1
                self.write_ind('  %s %s = it.Value();\n', c_item_type, temp_name)

                self.indent += 1

                self._write_tuple_unpacking(
                    temp_name, index_expr.items, item_type.items)

                self.indent -= 1
              else:
                raise AssertionError()

            else:
              raise AssertionError('Unexpected type %s' % item_type)

            if cond:
              self.indent += 1
              self.write_ind('if (')
              self.accept(cond[0])  # Just the first one
              self.write(') {\n')

            self.write_ind('  %s->append(', lval.name)
            self.accept(left_expr)
            self.write(');\n')

            if cond:
              self.write_ind('}\n')
              self.indent -= 1

            self.write_ind('}\n')
            return

          self.accept(o.rvalue)
          self.write(';\n')

        elif isinstance(lval, MemberExpr):
          self.write_ind('')
          self.accept(lval)
          self.write(' = ')
          self.accept(o.rvalue)
          self.write(';\n')

          if self.current_method_name in ('__init__', 'Reset'):
            # Collect statements that look like self.foo = 1
            # Only do this in __init__ so that a derived class mutating a field
            # from the base calss doesn't cause duplicate C++ fields.  (C++
            # allows two fields of the same name!)
            #
            # HACK for WordParser: also include Reset().  We could change them
            # all up front but I kinda like this.

            if isinstance(lval.expr, NameExpr) and lval.expr.name == 'self':
              #log('    lval.name %s', lval.name)
              lval_type = self.types[lval]
              self.member_vars[lval.name] = lval_type

        elif isinstance(lval, IndexExpr):  # a[x] = 1
          # d->set(x, 1) for both List and Dict
          self.write_ind('')
          self.accept(lval.base)
          self.write('->set(')
          self.accept(lval.index)
          self.write(', ')
          self.accept(o.rvalue)
          self.write(');\n')

        elif isinstance(lval, TupleExpr):
          # An assignment to an n-tuple turns into n+1 statements.  Example:
          #
          # x, y = mytuple
          #
          # Tuple2<int, Str*> tup1 = mytuple
          # int x = tup1->at0()
          # Str* y = tup1->at1()

          rvalue_type = self.types[o.rvalue]

          # type alias upgrade for MyPy 0.780
          if isinstance(rvalue_type, TypeAliasType):
            rvalue_type = rvalue_type.alias.target

          c_type = get_c_type(rvalue_type)

          is_return = isinstance(o.rvalue, CallExpr)
          if is_return:
            assert c_type.endswith('*')
            c_type = c_type[:-1]

          temp_name = 'tup%d' % self.unique_id
          self.unique_id += 1
          self.write_ind('%s %s = ', c_type, temp_name)

          self.accept(o.rvalue)
          self.write(';\n')

          self._write_tuple_unpacking(temp_name, lval.items, rvalue_type.items,
                                      is_return=is_return)

        else:
          raise AssertionError(lval)

    def _write_body(self, body):
        """Write a block without the { }."""
        for stmt in body:
            # Ignore things that look like docstrings
            if isinstance(stmt, ExpressionStmt) and isinstance(stmt.expr, StrExpr):
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
        if isinstance(o.expr, CallExpr) and isinstance(o.expr.callee, NameExpr):
          func_name = o.expr.callee.name

        # special case: 'for i in xrange(3)'
        if func_name == 'xrange':
          index_name = o.index.name
          args = o.expr.args
          num_args = len(args)

          if num_args == 1:  # xrange(end)
            self.write_ind('for (int %s = 0; %s < ', index_name, index_name)
            self.accept(args[0])
            self.write('; ++%s) ', index_name)

          elif num_args == 2:  # xrange(being, end)
            self.write_ind('for (int %s = ', index_name)
            self.accept(args[0])
            self.write('; %s < ', index_name)
            self.accept(args[1])
            self.write('; ++%s) ', index_name)

          elif num_args == 3:  # xrange(being, end, step)
            # Special case to detect a constant -1.  This is a static
            # heuristic, because it could be negative dynamically.  TODO:
            # mylib.reverse_xrange() or something?
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

        #self.log('  iterating over type %s', over_type)
        #self.log('  iterating over type %s', over_type.type.fullname)

        over_dict = False

        if over_type.type.fullname == 'builtins.list':
          c_type = get_c_type(over_type)
          assert c_type.endswith('*'), c_type
          c_iter_type = c_type.replace('List', 'ListIter', 1)[:-1]  # remove *

          # ReverseListIter!
          if reverse:
            c_iter_type = 'Reverse' + c_iter_type

        elif over_type.type.fullname == 'builtins.dict':
          # Iterator
          c_type = get_c_type(over_type)
          assert c_type.endswith('*'), c_type
          c_iter_type = c_type.replace('Dict', 'DictIter', 1)[:-1]  # remove *

          over_dict = True

          assert not reverse

        elif over_type.type.fullname == 'builtins.str':
          c_iter_type = 'StrIter'
          assert not reverse  # can't reverse iterate over string yet

        else:  # assume it's like d.iteritems()?  Iterator type
          assert False, over_type

        if index0_name:
          # can't initialize two things in a for loop, so do it on a separate line
          if self.decl:
            self.local_var_list.append((index0_name, 'int'))
          self.write_ind('%s = 0;\n', index0_name)
          index_update = ', ++%s' % index0_name
        else:
          index_update = ''

        self.write_ind('for (%s it(', c_iter_type)
        self.accept(iterated_over)  # the thing being iterated over
        self.write('); !it.Done(); it.Next()%s) {\n', index_update)

        # for x in it: ...
        # for i, x in enumerate(pairs): ...

        if isinstance(item_type, Instance) or index0_name:
          c_item_type = get_c_type(item_type)
          self.write_ind('  %s ', c_item_type)
          self.accept(index_expr)
          if over_dict:
            self.write(' = it.Key();\n')
          else: 
            self.write(' = it.Value();\n')

          # Register loop variable as a stack root.
          if not self.ret_val_rooting and CTypeIsManaged(c_item_type):
            self.write_ind('  StackRoots _for({&');
            self.accept(index_expr)
            self.write_ind('});\n')

        elif isinstance(item_type, TupleType):  # for x, y in pairs
          if over_dict:
            assert isinstance(o.index, TupleExpr), o.index
            index_items = o.index.items
            assert len(index_items) == 2, index_items
            assert len(item_type.items) == 2, item_type.items

            key_type = get_c_type(item_type.items[0])
            val_type = get_c_type(item_type.items[1])

            # TODO(StackRoots): k, v
            self.write_ind('  %s %s = it.Key();\n', key_type, index_items[0].name)
            self.write_ind('  %s %s = it.Value();\n', val_type, index_items[1].name)

          else:
            # Example:
            # for (ListIter it(mylist); !it.Done(); it.Next()) {
            #   Tuple2<int, Str*> tup1 = it.Value();
            #   int i = tup1->at0();
            #   Str* s = tup1->at1();
            #   log("%d %s", i, s);
            # }

            c_item_type = get_c_type(item_type)

            if isinstance(o.index, TupleExpr):
              # TODO(StackRoots)
              temp_name = 'tup%d' % self.unique_id
              self.unique_id += 1
              self.write_ind('  %s %s = it.Value();\n', c_item_type, temp_name)

              self.indent += 1

              self._write_tuple_unpacking(
                  temp_name, o.index.items, item_type.items)

              self.indent -= 1
            else:
              self.write_ind('  %s %s = it.Value();\n', c_item_type, o.index.name)
              #self.write_ind('  StackRoots _for(&%s)\n;', o.index.name)

        else:
          raise AssertionError('Unexpected type %s' % item_type)

        # Copy of visit_block, without opening {
        self.indent += 1
        block = o.body
        self._write_body(block.body)
        self.indent -= 1
        self.write_ind('}\n')

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
          self.write('\n')
        self.write_ind('case ')
        self.accept(arg)
        self.write(': ')

      self.accept(body)
      self.write_ind('  break;\n')

      if if_node.else_body:
        first_of_block = if_node.else_body.body[0]
        if isinstance(first_of_block, IfStmt):
          self._write_cases(first_of_block)
        else:
          # end the recursion
          self.write_ind('default: ')
          self.accept(if_node.else_body)  # the whole block
          # no break here

    def _write_switch(self, expr, o):
        """Write a switch statement over integers."""
        assert len(expr.args) == 1, expr.args

        self.write_ind('switch (')
        self.accept(expr.args[0])
        self.write(') {\n')

        assert len(o.body.body) == 1, o.body.body
        if_node = o.body.body[0]
        assert isinstance(if_node, IfStmt), if_node

        self.indent += 1
        self._write_cases(if_node)

        self.indent -= 1
        self.write_ind('}\n')

    def _write_typeswitch(self, expr, o):
        """Write a switch statement over ASDL types."""
        assert len(expr.args) == 1, expr.args

        self.write_ind('switch (')
        self.accept(expr.args[0])
        self.write('->tag_()) {\n')

        assert len(o.body.body) == 1, o.body.body
        if_node = o.body.body[0]
        assert isinstance(if_node, IfStmt), if_node

        self.indent += 1
        self._write_cases(if_node)

        self.indent -= 1
        self.write_ind('}\n')

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

        if expr.callee.name == 'switch':
          self._write_switch(expr, o)
        elif expr.callee.name == 'tagswitch':
          self._write_typeswitch(expr, o)
        else:
          assert isinstance(expr, CallExpr), expr
          self.write_ind('{  // with\n')
          self.indent += 1

          self.write_ind('')
          self.accept(expr.callee)
          self.write(' ctx(')
          for i, arg in enumerate(expr.args):
            if i != 0:
              self.write(', ')
            self.accept(arg)
          self.write(');\n\n')

          #self.write_ind('')
          self._write_body(o.body.body)

          self.indent -= 1
          self.write_ind('}\n')

    def visit_del_stmt(self, o: 'mypy.nodes.DelStmt') -> T:

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
                'Use mylib.maybe_remove(d, key) instead of del d[key]')

          self.write(';\n')

    def _WriteFuncParams(self, arg_types, arguments, update_locals=False):
        """Write params and optionally mutate self.local_vars."""
        first = True  # first NOT including self
        for arg_type, arg in zip(arg_types, arguments):
          if not first:
            self.decl_write(', ')

          # TODO: Turn this on.  Having stdlib problems, e.g.
          # examples/cartesian.
          c_type = get_c_type(arg_type, param=False)
          #c_type = get_c_type(arg_type, param=True)

          arg_name = arg.variable.name

          # C++ has implicit 'this'
          if arg_name == 'self':
            continue

          self.decl_write('%s %s', c_type, arg_name)
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

    def _WithOneLessArg(self, o, class_name, ret_type):
      default_val = o.arguments[-1].initializer
      if default_val:  # e.g. osh/bool_parse.py has default val
        if self.decl or class_name is None:
          func_name = o.name
        else:
          func_name = '%s::%s' % (self.current_class_name, o.name)
        self.write('\n')

        # Write _Next() with no args
        virtual = ''  # Note: the extra method can NEVER be virtual?
        c_ret_type = get_c_type(ret_type)
        if isinstance(ret_type, TupleType):
          assert c_ret_type.endswith('*')
          c_ret_type = c_ret_type[:-1]

        self.decl_write_ind('%s%s %s(', virtual, c_ret_type, func_name)

        # Write all params except last optional one
        self._WriteFuncParams(o.type.arg_types[:-1], o.arguments[:-1])

        self.decl_write(')')
        if self.decl:
          self.decl_write(';\n')
        else:
          self.write(' {\n')
          # return MakeOshParser()
          kw = '' if isinstance(ret_type, NoneTyp) else 'return '
          self.write('  %s%s(' % (kw, o.name))

          # Don't write self or last optional argument
          first_arg_index = 0 if class_name is None else 1
          pass_through = o.arguments[first_arg_index:-1]

          if pass_through:
            for i, arg in enumerate(pass_through):
              if i != 0:
                self.write(', ')
              self.write(arg.variable.name)
            self.write(', ')

          # Now write default value, e.g. lex_mode_e::DBracket
          self.accept(default_val)  
          self.write(');\n')
          self.write('}\n')

    def visit_func_def(self, o: 'mypy.nodes.FuncDef') -> T:
        if o.name == '__repr__':  # Don't translate
          return

        # No function prototypes when forward declaring.
        if self.forward_decl:
          self.virtual.OnMethod(self.current_class_name, o.name)
          return

        # Hacky MANUAL LIST of functions and methods with OPTIONAL ARGUMENTS.
        #
        # For example, we have a method like this:
        #   MakeOshParser(_Reader* line_reader, bool emit_comp_dummy)
        #
        # And we want to write an EXTRA C++ method like this:
        #   MakeOshParser(_Reader* line_reader) {
        #     return MakeOshParser(line_reader, true);
        #   }

        # TODO: restrict this
        class_name = self.current_class_name
        func_name = o.name
        ret_type = o.type.ret_type

        if (class_name in ('BoolParser', 'CommandParser') and
              func_name == '_Next' or
            class_name == 'ParseContext' and func_name == 'MakeOshParser' or
            class_name == 'ErrorFormatter' and func_name == 'PrettyPrintError' or
            class_name is None and func_name == 'PrettyPrintError' or
            class_name == 'WordParser' and
              func_name in ('_ParseVarExpr', '_ReadVarOpArg2') or
            class_name == 'AbstractWordEvaluator' and 
              func_name in ('EvalWordSequence2', '_EmptyStrOrError') or
            # virtual method in several classes
            func_name == 'EvalWordToString' or
            class_name == 'ArithEvaluator' and func_name == '_ValToIntOrError' or
            class_name == 'BoolEvaluator' and
              func_name in ('_EvalCompoundWord', '_StringToIntegerOrError') or
            class_name == 'CommandEvaluator' and
              func_name in ('_Execute', 'ExecuteAndCatch') or
            # core/executor.py
            class_name == 'ShellExecutor' and func_name == '_MakeProcess' or
            # osh/word_eval.py
            class_name is None and func_name == 'ShouldArrayDecay' or
            # core/state.py
            class_name is None and func_name in ('_PackFlags', 'OshLanguageSetValue') or
            class_name == 'Mem' and
              func_name in ('GetValue', 'SetValue', 'GetCell',
                            '_ResolveNameOrRef') or
            class_name == 'SearchPath' and func_name == 'Lookup' or
            # core/ui.py
            class_name == 'ErrorFormatter' and
              func_name in ('Print_', 'PrintMessage') or
            func_name == 'GetLineSourceString' or
            # osh/sh_expr_eval.py
            class_name is None and func_name == 'EvalLhsAndLookup' or
            class_name == 'SplitContext' and
              func_name in ('SplitForWordEval', '_GetSplitter') or
            # qsn_/qsn.py
            class_name is None and 
              func_name in ('maybe_encode', 'maybe_shell_encode') or
            # osh/builtin_assign.py
            class_name is None and func_name == '_PrintVariables' or
            # virtual function
            func_name == 'RunSimpleCommand' or
            # core/main_loop.py
            func_name == 'Batch'
          ):
          self._WithOneLessArg(o, class_name, ret_type)

        virtual = ''
        if self.decl:
          self.local_var_list = []  # Make a new instance to collect from
          self.local_vars[o] = self.local_var_list

          #log('Is Virtual? %s %s', self.current_class_name, o.name)
          if self.virtual.IsVirtual(self.current_class_name, o.name):
            virtual = 'virtual '

        if not self.decl and self.current_class_name:
          # definition looks like
          # void Type::foo(...);
          func_name = '%s::%s' % (self.current_class_name, o.name)
        else:
          # declaration inside class { }
          func_name = o.name

        self.write('\n')

        c_ret_type, _ = get_c_return_type(ret_type)

        self.decl_write_ind('%s%s %s(', virtual, c_ret_type, func_name)

        self._WriteFuncParams(o.type.arg_types, o.arguments, update_locals=True)

        if self.decl:
          self.decl_write(');\n')
          self.current_func_node = o
          self.accept(o.body)  # Collect member_vars, but don't write anything
          self.current_func_node = None
          return

        self.write(') ')

        # Write local vars we collected in the 'decl' phase
        if not self.forward_decl and not self.decl:
          arg_names = [arg.variable.name for arg in o.arguments]
          #log('arg_names %s', arg_names)
          #log('local_vars %s', self.local_vars[o])
          self.prepend_to_block = [
              (lval_name, c_type, lval_name in arg_names)
              for (lval_name, c_type) in self.local_vars[o]
          ]

        self.current_func_node = o
        self.accept(o.body)
        self.current_func_node = None

    def visit_overloaded_func_def(self, o: 'mypy.nodes.OverloadedFuncDef') -> T:
        pass

    def visit_class_def(self, o: 'mypy.nodes.ClassDef') -> T:
        #log('  CLASS %s', o.name)

        base_class_name = None  # single inheritance only
        for b in o.base_type_exprs:
          if isinstance(b, NameExpr):
            # TODO: inherit from std::exception?
            if b.name != 'object' and b.name != 'Exception':
              base_class_name = b.name
          elif isinstance(b, MemberExpr): # vm._Executor -> vm::_Executor
            assert isinstance(b.expr, NameExpr), b
            base_class_name = '%s::%s' % (b.expr.name, b.name)

        # Forward declare types because they may be used in prototypes
        if self.forward_decl:
          self.decl_write_ind('class %s;\n', o.name)
          if base_class_name:
            self.virtual.OnSubclass(base_class_name, o.name)
          # Visit class body so we get method declarations
          self.current_class_name = o.name
          self._write_body(o.defs.body)
          self.current_class_name = None
          return

        if self.decl:
          self.member_vars.clear()  # make a new list

          self.decl_write_ind('class %s', o.name)  # block after this

          # e.g. class TextOutput : public ColorOutput
          self.decl_write(' : public %s', base_class_name or 'Obj')

          self.decl_write(' {\n')
          self.decl_write_ind(' public:\n')

          # NOTE: declaration still has to traverse the whole body to fill out
          # self.member_vars!!!
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
                self.decl_write_ind('%s(', o.name)
                self._WriteFuncParams(stmt.type.arg_types, stmt.arguments)
                self.decl_write(');\n')

                # Visit for member vars
                self.current_method_name = method_name
                self.accept(stmt.body)
                self.current_method_name = None
                continue

              if method_name == '__enter__':
                continue

              if method_name == '__exit__':
                # Turn it into a destructor with NO ARGS
                self.decl_write_ind('~%s();\n', o.name)
                continue

              if method_name == '__repr__':
                # skip during declaration, just like visit_func_def does during definition
                continue

              # Any other function: Visit for member vars
              self.current_method_name = method_name
              self.accept(stmt)
              self.current_method_name = None
              continue

            # Do we need this?  I think everything under a class is a method?
            self.accept(stmt)

          # List of field mask expressions

          if self.virtual.HasVTable(o.name):  # Account for vtable pointer offset
            mask_func_name = 'maskbit_v'
          else:
            mask_func_name = 'maskbit'

          bits = []
          for name in sorted(self.member_vars):
            c_type = get_c_type(self.member_vars[name])
            if CTypeIsManaged(c_type):
              bits.append('%s(offsetof(%s, %s))' % (mask_func_name, o.name, name))
          if bits:
            self.mask_funcs[o] = 'maskof_%s()' % o.name

          # Now write member defs
          #log('MEMBERS for %s: %s', o.name, list(self.member_vars.keys()))
          if self.member_vars:
            self.decl_write('\n')  # separate from functions
            for name in sorted(self.member_vars):
              c_type = get_c_type(self.member_vars[name])
              self.decl_write_ind('%s %s;\n', c_type, name)

          self.current_class_name = None

          self.decl_write('\n')
          self.decl_write_ind('DISALLOW_COPY_AND_ASSIGN(%s)\n', o.name)
          self.indent -= 1
          self.decl_write_ind('};\n')
          self.decl_write('\n')

          if bits:
            self.decl_write('constexpr uint16_t maskof_%s() {\n', o.name)

            self.decl_write('  return\n')
            self.decl_write('    ')
            self.decl_write('\n  | '.join(bits))
            self.decl_write(';\n')

            self.decl_write('}\n')
            self.decl_write('\n')

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
              self.write('\n')
              self.write('%s::%s(', o.name, o.name)
              self._WriteFuncParams(stmt.type.arg_types, stmt.arguments)
              self.write(') ')

              # Base class can use Obj() constructor directly, but Derived class can't
              if not base_class_name:
                if o in self.mask_funcs:
                  mask_str = 'maskof_%s()' % o.name
                else: 
                  mask_str = 'kZeroMask'

                self.write('\n')
                self.write(
                    '    : Obj(Tag::FixedSize, %s, sizeof(%s)) ' % (mask_str, o.name))

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
                if isinstance(callee, MemberExpr) and callee.name == '__init__':
                  base_constructor_args = expr.args
                  #log('ARGS %s', base_constructor_args)
                  self.write(': %s(', base_class_name)
                  for i, arg in enumerate(base_constructor_args):
                    if i == 0:
                      continue  # Skip 'this'
                    if i != 1:
                      self.write(', ')
                    self.accept(arg)
                  self.write(')')

                  first_index += 1

              self.write(' {\n')

              # Derived classes MUTATE the mask
              if base_class_name:
                mask_str = self.mask_funcs.get(o)
                if mask_str is None:
                  #self.log('*** No mask for %s', o.name)
                  pass
                else:
                  self.write('  field_mask_ |= %s;\n' % mask_str)

              # Now visit the rest of the statements
              self.indent += 1
              for node in stmt.body.body[first_index: ]:
                self.accept(node)
              self.indent -= 1
              self.write('}\n')

              continue  # wrote FuncDef for constructor


            if stmt.name == '__enter__':
              continue

            if stmt.name == '__exit__':
              self.decl_write('\n')
              self.decl_write_ind('%s::~%s()', o.name, o.name)
              self.accept(stmt.body)
              continue

            self.accept(stmt)

        self.current_class_name = None   # Stop prefixing functions with class

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
        pass

    def visit_import_from(self, o: 'mypy.nodes.ImportFrom') -> T:
        if self.decl:  # No duplicate 'using'
          return

        if o.id in ('__future__', 'typing'):
          return  # do nothing

        # Later we need to turn module.func() into module::func(), without
        # disturbing self.foo.
        for name, alias in o.names:
          if alias:
            self.imported_names.add(alias)
          else:
            self.imported_names.add(name)

        for name, alias in o.names:

          #self.log('ImportFrom id: %s name: %s alias: %s', o.id, name, alias)

          # TODO: Should these be moved to core/pylib.py or something?
          # They are varargs functions that have to be rewritten.
          if name in ('log', 'p_die', 'e_die', 'e_die_status', 'e_strict',
                      'e_usage', 'stderr_line'):
            continue    # do nothing

          # mylib
          if name in ('switch', 'tagswitch', 'iteritems', 'str_cmp',
                      'NewDict'):
            continue  # do nothing

          # A heuristic that works for the Oil import style.
          if '.' in o.id:
            # from core.pyerror import log => using core::util::log
            translate_import = True
          else:
            # from core import util => NOT translated
            # We just rely on 'util' being defined.
            translate_import = False

          if translate_import:
            dotted_parts = o.id.split('.')
            last_dotted = dotted_parts[-1]

            # Omit these:
            #   from _gen.oil_lang import grammar_nt
            if last_dotted == 'oil_lang':
              return
            #   from _devbuild.gen import syntax_asdl
            if last_dotted == 'gen':
              return

            # ASDL:
            #
            # namespaces:
            #   expr_e::Const   # Compound sum
            #   expr::Const
            #   Id
            #
            # types:
            #   expr__Const
            #   expr_t   # sum type
            #   expr_context_e   # simple sum.   This one is hard
            #   double_quoted
            #   Id_str

            # Tag numbers/namespaces end with _n.  enum types end with _e.
            # TODO: rename special cases

            is_namespace = False

            if last_dotted.endswith('_asdl'):
              if name.endswith('_n') or name.endswith('_i') or name in (
                'Id', 'hnode_e', 'source_e', 'place_e',

                # syntax_asdl
                'bracket_op', 'bracket_op_e',
                'source', 'source_e',
                'suffix_op', 'suffix_op_e',

                'sh_lhs_expr', 'parse_result',

                'command_e', 'command', 
                'condition_e', 'condition', 
                'for_iter_e', 'for_iter', 
                'arith_expr_e', 'arith_expr',
                'bool_expr_e', 'bool_expr',
                'expr_e', 'expr',
                'place_expr_e', 'place_expr', 
                'word_part_e', 'word_part', 
                'word_e', 'word',
                'redir_loc_e', 'redir_loc',
                'redir_param_e', 'redir_param',
                'proc_sig_e', 'proc_sig',

                'glob_part_e', 'glob_part',

                're_e', 're',
                're_repeat_e', 're_repeat',
                'class_literal_term_e', 'class_literal_term',
                'char_class_term_e', 'char_class_term',

                'sh_lhs_expr_e', 'sh_lhs_expr',
                'variant_type',

                # runtime_asdl
                'flag_type_e', 'flag_type',
                'lvalue_e', 'lvalue',
                'value_e', 'value',
                'part_value_e', 'part_value',
                'cmd_value_e', 'cmd_value',
                'redirect_arg_e', 'redirect_arg',
                'a_index_e', 'a_index',
                'parse_result_e',
                'printf_part_e', 'printf_part',
                'wait_status', 'wait_status_e',
                'trace', 'trace_e',
                ):
                is_namespace = True

            if is_namespace:
              # No aliases yet?
              #lhs = alias if alias else name
              self.write_ind(
                  'namespace %s = %s::%s;\n', name, last_dotted, name)
            else:
              if alias:
                # using runtime_asdl::emit_e = EMIT;
                self.write_ind('using %s = %s::%s;\n', alias, last_dotted, name)
              else:
                if 0:
                  self.write_ind('using %s::%s;\n', '::'.join(dotted_parts), name)
                else:
                  #   from _devbuild.gen.id_kind_asdl import Id
                  # -> using id_kind_asdl::Id.
                  self.write_ind('using %s::%s;\n', last_dotted, name)
          else:
            # If we're importing a module without an alias, we don't need to do
            # anything.  'namespace cmd_eval' is already defined.
            if not alias:
              return

            #    from asdl import format as fmt
            # -> namespace fmt = format;
            self.write_ind('namespace %s = %s;\n', alias, name)

        # Old scheme
        # from testpkg import module1 =>
        # namespace module1 = testpkg.module1;
        # Unfortunately the MyPy AST doesn't have enough info to distinguish
        # imported packages and functions/classes?

    def visit_import_all(self, o: 'mypy.nodes.ImportAll') -> T:
        pass

    # Statements

    def visit_block(self, block: 'mypy.nodes.Block') -> T:
        self.write('{\n')  # not indented to use same line as while/if

        self.indent += 1

        if self.prepend_to_block:
          done = set()
          for lval_name, c_type, is_param in self.prepend_to_block:
            if not is_param and lval_name not in done:
              rhs = ' = nullptr' if CTypeIsManaged(c_type) else ''
              self.write_ind('%s %s%s;\n', c_type, lval_name, rhs)
              done.add(lval_name)

          # Figure out if we have any roots to write with StackRoots
          roots = []  # keep it sorted
          for lval_name, c_type, is_param in self.prepend_to_block:
            #self.log('%s %s %s', lval_name, c_type, is_param)
            if lval_name not in roots and CTypeIsManaged(c_type):
              roots.append(lval_name)
          #self.log('roots %s', roots)

          if self.ret_val_rooting:
            self.write_ind('RootsFrame _r{FUNC_NAME};\n')
          else:
            if len(roots):
              self.write_ind('StackRoots _roots({');
              for i, r in enumerate(roots):
                if i != 0:
                  self.write(', ')
                self.write('&%s' % r)

              self.write('});\n')
              self.write('\n')

          self.prepend_to_block = None

        self._write_body(block.body)

        self.indent -= 1
        self.write_ind('}\n')

    def visit_expression_stmt(self, o: 'mypy.nodes.ExpressionStmt') -> T:
        # TODO: Avoid writing docstrings.
        # If it's just a string, then we don't need it.

        self.write_ind('')
        self.accept(o.expr)
        self.write(';\n')

    def visit_operator_assignment_stmt(self, o: 'mypy.nodes.OperatorAssignmentStmt') -> T:
        self.write_ind('')
        self.accept(o.lvalue)
        self.write(' %s= ', o.op)  # + to +=
        self.accept(o.rvalue)
        self.write(';\n')

    def visit_while_stmt(self, o: 'mypy.nodes.WhileStmt') -> T:
        self.write_ind('while (')
        self.accept(o.expr)
        self.write(') ')
        self.accept(o.body)

    def visit_return_stmt(self, o: 'mypy.nodes.ReturnStmt') -> T:
        if self.ret_val_rooting:
          if o.expr:
            # Don't handle 'return None' here
            if not (isinstance(o.expr, NameExpr) and o.expr.name == 'None'):

              # Note: the type of the return expression (self.types[o.expr])
              # and the return type of the FUNCTION are different.  Use the
              # latter.
              ret_type = self.current_func_node.type.ret_type

              c_ret_type, returning_tuple = get_c_return_type(ret_type)

              # return '', None  # tuple literal
              #   but NOT
              # return tuple_func()
              if returning_tuple and isinstance(o.expr, TupleExpr):

                # Figure out which ones we have to root
                item_temp_names = []
                for i, item in enumerate(o.expr.items):
                  item_type = self.types[item]
                  item_c_type = get_c_type(item_type)
                  if CTypeIsManaged(item_c_type):
                    var_name = 'tmp_item%d' % i
                    self.write_ind('%s %s = ', item_c_type, var_name)
                    self.accept(item)
                    self.write(';\n')

                    self.write_ind('gHeap.RootOnReturn(reinterpret_cast<Obj*>(%s));\n' % var_name)
                    item_temp_names.append(var_name)

                  else:
                    item_temp_names.append(None)

                self.write_ind('return %s(' % c_ret_type)
                for i, item in enumerate(o.expr.items):
                  if i != 0:
                    self.write(', ')

                  var_name = item_temp_names[i]
                  if var_name is not None:
                    self.write(var_name)
                  else:
                    self.accept(item)
                self.write(');\n')

                return

              if CTypeIsManaged(c_ret_type):
                self.write_ind('%s tmp_ret = ', c_ret_type)
                self.accept(o.expr)
                self.write(';\n')

                self.write_ind('gHeap.RootOnReturn(reinterpret_cast<Obj*>(tmp_ret));\n')
                self.write_ind('return tmp_ret;\n')
                return

        # OLD return value rooting.

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

            c_ret_type, returning_tuple = get_c_return_type(ret_type)

            # return '', None  # tuple literal
            #   but NOT
            # return tuple_func()
            if returning_tuple and isinstance(o.expr, TupleExpr):
              self.write_ind('%s(' % c_ret_type)
              for i, item in enumerate(o.expr.items):
                if i != 0:
                  self.write(', ')
                self.accept(item)
              self.write(');\n')
              return

          # Not returning tuple
          self.accept(o.expr)

        self.write(';\n')

    def visit_assert_stmt(self, o: 'mypy.nodes.AssertStmt') -> T:
        pass

    def visit_if_stmt(self, o: 'mypy.nodes.IfStmt') -> T:
        # Not sure why this wouldn't be true
        assert len(o.expr) == 1, o.expr

        # Omit anything that looks like if __name__ == ...
        cond = o.expr[0]

        if isinstance(cond, UnaryExpr) and cond.op == 'not':
          # check 'if not mylist'
          cond_expr = cond.expr
        else:
          # TODO: if x > 0 and mylist
          #       if x > 0 and not mylist , etc.
          cond_expr = cond

        cond_type = self.types[cond_expr]

        if not _CheckConditionType(cond_type):
          raise AssertionError(
              "Can't use str, list, or dict in boolean context")

        if (isinstance(cond, ComparisonExpr) and
            isinstance(cond.operands[0], NameExpr) and 
            cond.operands[0].name == '__name__'):
          return

        # Omit if 0:
        if isinstance(cond, IntExpr) and cond.value == 0:
          return

        # Omit if TYPE_CHECKING blocks.  They contain type expressions that
        # don't type check!
        if isinstance(cond, NameExpr) and cond.name == 'TYPE_CHECKING':
          return
        # mylib.CPP
        if isinstance(cond, MemberExpr) and cond.name == 'CPP':
          # just take the if block
          self.write_ind('// if MYCPP\n')
          self.write_ind('')
          for node in o.body:
            self.accept(node)
          self.write_ind('// endif MYCPP\n')
          return
        # mylib.PYTHON
        if isinstance(cond, MemberExpr) and cond.name == 'PYTHON':
          if o.else_body:
            self.write_ind('// if not PYTHON\n')
            self.write_ind('')
            self.accept(o.else_body)
            self.write_ind('// endif MYCPP\n')
          return

        self.write_ind('if (')
        for e in o.expr:
          self.accept(e)
        self.write(') ')

        for node in o.body:
          self.accept(node)

        if o.else_body:
          self.write_ind('else ')
          self.accept(o.else_body)

    def visit_break_stmt(self, o: 'mypy.nodes.BreakStmt') -> T:
        self.write_ind('break;\n')

    def visit_continue_stmt(self, o: 'mypy.nodes.ContinueStmt') -> T:
        self.write_ind('continue;\n')

    def visit_pass_stmt(self, o: 'mypy.nodes.PassStmt') -> T:
        self.write_ind(';  // pass\n')

    def visit_raise_stmt(self, o: 'mypy.nodes.RaiseStmt') -> T:
        # C++ compiler is aware of assert(0) for unreachable code
        if (o.expr and 
            isinstance(o.expr, CallExpr) and
            o.expr.callee.name == 'AssertionError'):
          self.write_ind('assert(0);  // AssertionError\n')
          return

        self.write_ind('throw ')
        # it could be raise -> throw ; .  OSH uses that.
        if o.expr:
          self.accept(o.expr)
        self.write(';\n')

    def visit_try_stmt(self, o: 'mypy.nodes.TryStmt') -> T:
        self.write_ind('try ')
        self.accept(o.body)
        caught = False
        for t, v, handler in zip(o.types, o.vars, o.handlers):

          # Heuristic
          if isinstance(t, MemberExpr):
            c_type = '%s::%s*' % (t.expr.name, t.name)
          elif isinstance(t, TupleExpr):
            c_type = None
            if len(t.items) == 2:
              e1 = t.items[0]
              e2 = t.items[1]
              if isinstance(e1, NameExpr) and isinstance(e2, NameExpr):
                names = [e1.name, e2.name]
                names.sort()
                if names == ['IOError', 'OSError']:
                  c_type = 'IOError_OSError*'  # Base class in mylib

            if c_type is None:
              c_type = 'MultipleExceptions'  # Causes compile error
          else:
            c_type = '%s*' % t.name

          if v:
            self.write_ind('catch (%s %s) ', c_type, v.name)
          else:
            self.write_ind('catch (%s) ', c_type)
          self.accept(handler)

          caught = True

        # DUMMY to prevent compile errors
        # TODO: Remove this
        if not caught:
          self.write_ind('catch (std::exception const&) { }\n')

        #if o.else_body:
        #  raise AssertionError('try/else not supported')
        #if o.finally_body:
        #  raise AssertionError('try/finally not supported')

    def visit_print_stmt(self, o: 'mypy.nodes.PrintStmt') -> T:
        pass

    def visit_exec_stmt(self, o: 'mypy.nodes.ExecStmt') -> T:
        pass

