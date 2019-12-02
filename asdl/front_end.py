"""
front_end.py: Lexer and parser for the ASDL schema language.
"""
from __future__ import print_function

import re

from asdl import asdl_ as asdl
from asdl import meta
from asdl.asdl_ import Use, Module, Type, Constructor, Field, Sum, Product

_KEYWORDS = ['use', 'module', 'attributes']

_TOKENS = [
    ('Keyword', ''),
    ('Name', ''),

    # For operators, the string matters
    ('Equals', '='),
    ('Comma', ','),
    ('Question', '?'),
    ('Pipe', '|'),
    ('Asterisk', '*'),
    ('LParen', '('),
    ('RParen', ')'),
    ('LBrace', '{'),
    ('RBrace', '}'),
    ('Percent', '%'),
]

_TOKEN_STR = [name for name, _ in _TOKENS]  # integer -> string like LParen
_TOKEN_INT = {}  # string like '(' -> integer


class TokenKind(object):
    """ASDL tokens.

    TokenKind.LBrace = 5, etc.
    """
    pass


for i, (name, val) in enumerate(_TOKENS):
    setattr(TokenKind, name, i)
    _TOKEN_INT[val] = i


class Token(object):
    def __init__(self, kind, value, lineno):
        self.kind = kind
        self.value = value
        self.lineno = lineno

class ASDLSyntaxError(Exception):
    def __init__(self, msg, lineno=None):
        self.msg = msg
        self.lineno = lineno or '<unknown>'

    def __str__(self):
        return 'Syntax error on line {0.lineno}: {0.msg}'.format(self)

def _Tokenize(f):
    """Tokenize the given buffer. Yield Token objects."""
    for lineno, line in enumerate(f, 1):
        for m in re.finditer(r'\s*(\w+|--.*|.)', line.strip()):
            c = m.group(1)
            if c in _KEYWORDS:
                yield Token(TokenKind.Keyword, c, lineno)
            elif c[0].isalpha():
                yield Token(TokenKind.Name, c, lineno)
            elif c[:2] == '--':
                # Comment
                break
            else:
                # Operators
                try:
                    op_kind = _TOKEN_INT[c]
                except KeyError:
                    raise ASDLSyntaxError('Invalid operator %s' % c, lineno)
                yield Token(op_kind, c, lineno)

class ASDLParser(object):
    """Parser for ASDL files.

    Create, then call the parse method on a buffer containing ASDL.
    This is a simple recursive descent parser that uses _Tokenize for the
    lexing.
    """
    def __init__(self):
        self._tokenizer = None
        self.cur_token = None

    def parse(self, f):
        """Parse the ASDL in the file and return an AST with a Module root.
        """
        self._tokenizer = _Tokenize(f)
        self._advance()
        return self._parse_module()

    def _parse_module(self):
        """
        module = 'module' NAME '{' use* type* '}'
        """
        if not self._at_keyword('module'):
            raise ASDLSyntaxError(
                'Expected "module" (found {})'.format(self.cur_token.value),
                self.cur_token.lineno)
        self._advance()
        name = self._match(TokenKind.Name)
        self._match(TokenKind.LBrace)

        uses = []
        while self._at_keyword('use'):
            uses.append(self._parse_use())

        defs = []
        while self.cur_token.kind == TokenKind.Name:
            typename = self._advance()
            self._match(TokenKind.Equals)
            type_ = self._parse_type()
            defs.append(Type(typename, type_))

        self._match(TokenKind.RBrace)
        return Module(name, uses, defs)

    def _parse_use(self):
        """
        use = 'use' NAME '{' NAME+ '}'
        """
        self._advance()
        mod_name = self._match(TokenKind.Name)
        self._match(TokenKind.LBrace)

        type_names = []
        while self.cur_token.kind == TokenKind.Name:
            t = self._advance()
            type_names.append(t)
            if self.cur_token.kind == TokenKind.RParen:
                break
            elif self.cur_token.kind == TokenKind.Comma:
                self._advance()

        self._match(TokenKind.RBrace)
        return Use(mod_name, type_names)

    def _parse_type(self):
        """
        constructor: Name fields?
        sum: constructor ('|' constructor)*
        type: product | sum
        """
        if self.cur_token.kind == TokenKind.LParen:
            # If we see a (, it's a product
            return self._parse_product()
        else:
            # Otherwise it's a sum. Look for ConstructorId
            sumlist = []
            while True:
                cons_name = self._match(TokenKind.Name)

                shared_type = None
                fields = None
                if self.cur_token.kind == TokenKind.LParen:
                    fields = self._parse_fields()
                elif self.cur_token.kind == TokenKind.Percent:
                    self._advance()
                    shared_type = self._match(TokenKind.Name)
                else:
                    pass

                cons = Constructor(cons_name, shared_type, fields)
                sumlist.append(cons)

                if self.cur_token.kind != TokenKind.Pipe:
                  break
                self._advance()
            return Sum(sumlist, self._parse_optional_attributes())

    def _parse_product(self):
        return Product(self._parse_fields(), self._parse_optional_attributes())

    def _parse_fields(self):
        fields = []
        self._match(TokenKind.LParen)
        while self.cur_token.kind == TokenKind.Name:
            typename = self._advance()
            is_seq, is_opt = self._parse_optional_field_quantifier()
            if self.cur_token.kind == TokenKind.Name:
                id_ = self._advance()
            else:
                id_ = None
            fields.append(Field(typename, id_, seq=is_seq, opt=is_opt))
            if self.cur_token.kind == TokenKind.RParen:
                break
            elif self.cur_token.kind == TokenKind.Comma:
                self._advance()
        self._match(TokenKind.RParen)
        return fields

    def _parse_optional_attributes(self):
        if self._at_keyword('attributes'):
            self._advance()
            return self._parse_fields()
        else:
            return None

    def _parse_optional_field_quantifier(self):
        is_seq, is_opt = False, False
        if self.cur_token.kind == TokenKind.Asterisk:
            is_seq = True
            self._advance()
        elif self.cur_token.kind == TokenKind.Question:
            is_opt = True
            self._advance()
        return is_seq, is_opt

    def _advance(self):
        """ Return the value of the current token and read the next one into
            self.cur_token.
        """
        cur_val = None if self.cur_token is None else self.cur_token.value
        try:
            self.cur_token = next(self._tokenizer)
        except StopIteration:
            self.cur_token = None
        return cur_val

    def _match(self, kind):
        """The 'match' primitive of RD parsers.

        * Verifies that the current token is of the given kind (kind can
          be a tuple, in which the kind must match one of its members).
        * Returns the value of the current token
        * Reads in the next token

        Args:
          kind: A TokenKind, or a tuple of TokenKind
        """
        if self.cur_token.kind == kind:
            value = self.cur_token.value
            self._advance()
            return value
        else:
            raise ASDLSyntaxError(
                'Expected token {}, got {}'.format(_TOKEN_STR[kind],
                                                   self.cur_token.value),
                self.cur_token.lineno)

    def _at_keyword(self, keyword):
        return (self.cur_token.kind == TokenKind.Keyword and
                self.cur_token.value == keyword)


# A generic visitor for the meta-AST that describes ASDL. This can be used by
# emitters. Note that this visitor does not provide a generic visit method, so a
# subclass needs to define visit methods from visitModule to as deep as the
# interesting node.
# We also define a Check visitor that makes sure the parsed ASDL is well-formed.

class _VisitorBase(object):
    """Generic tree visitor for ASTs."""
    def __init__(self):
        self.cache = {}

    def visit(self, obj, *args):
        klass = obj.__class__
        meth = self.cache.get(klass)
        if meth is None:
            methname = "visit" + klass.__name__
            meth = getattr(self, methname, None)
            self.cache[klass] = meth
        if meth:
            try:
                meth(obj, *args)
            except Exception as e:
                print("Error visiting %r: %s" % (obj, e))
                raise


class Check(_VisitorBase):
    """A visitor that checks a parsed ASDL tree for correctness.

    Errors are printed and accumulated.
    """
    def __init__(self):
        super(Check, self).__init__()
        self.cons = {}
        self.errors = 0  # No longer used, but maybe in the future?
        self.types = {}  # list of declared field types

    def visitModule(self, mod):
        for dfn in mod.dfns:
            self.visit(dfn)

    def visitType(self, type):
        self.visit(type.value, str(type.name))

    def visitSum(self, sum, name):
        for t in sum.types:
            # Simple sum types can't conflict
            if asdl.is_simple(sum):
                continue
            self.visit(t, name)

    def visitConstructor(self, cons, name):
        for f in cons.fields:
            self.visit(f, cons.name)

    def visitField(self, field, name):
        key = str(field.type)
        l = self.types.setdefault(key, [])
        l.append(name)

    def visitProduct(self, prod, name):
        for f in prod.fields:
            self.visit(f, name)


def _AppendFields(field_ast_nodes, type_lookup, out):
  for field in field_ast_nodes:
    #print(field)
    runtime_type = type_lookup[field.type]

    # TODO: cache these under 'type*' and 'type?'.  Don't want duplicates!
    if field.seq:
      runtime_type = meta.ArrayType(runtime_type)

    if field.opt:
      runtime_type = meta.MaybeType(runtime_type)

    out.append((field.name, runtime_type))


def _MakeReflection(module, app_types):
  # Types that fields are declared with: int, id, word_part, etc.
  # Fields are NOT declared with Constructor names.
  type_lookup = dict(meta.BUILTIN_TYPES)
  type_lookup.update(app_types)

  # TODO: Need to resolve 'imports' to the right descriptor.  Code generation
  # relies on it:
  # - To pick the method to call in AbbreviatedTree etc.
  # - To generate 'value_t' instead of 'value' in type annotations.

  for u in module.uses:
    for type_name in u.type_names:
      type_lookup[type_name] = None  # Placeholder

  # NOTE: We need two passes because types can be mutually recursive, e.g.
  # asdl/arith.asdl.

  # First pass: collect declared types and make entries for them.
  for d in module.dfns:
    ast_node = d.value
    if isinstance(ast_node, asdl.Product):
      type_lookup[d.name] = meta.CompoundType([])

    elif isinstance(ast_node, asdl.Sum):
      is_simple = asdl.is_simple(ast_node)

      simple_variants = []
      if is_simple:
        simple_variants = [cons.name for cons in ast_node.types]
      type_lookup[d.name] = meta.SumType(is_simple, simple_variants)

    else:
      raise AssertionError(ast_node)

  # Second pass: resolve type declarations in Product and constructor.
  for d in module.dfns:
    ast_node = d.value
    if isinstance(ast_node, asdl.Product):
      runtime_type = type_lookup[d.name] 
      _AppendFields(ast_node.fields, type_lookup, runtime_type.fields)

    elif isinstance(ast_node, asdl.Sum):
      sum_type = type_lookup[d.name]  # the one we just created
      # TODO: Remove this -- it used to be used for runtime type checking.
      # Unused?
      if 1:
        for cons in ast_node.types:
          fields_out = []
          # fully-qualified name.  Use a _ so we can share strings with class
          # name.
          key = '%s__%s' % (d.name, cons.name)
          cons_type = meta.CompoundType(fields_out)
          type_lookup[key] = cons_type
          _AppendFields(cons.fields, type_lookup, fields_out)

          sum_type.cases.append(cons_type)

    else:
      raise AssertionError(ast_node)

  return type_lookup


def LoadSchema(f, app_types, verbose=False):
  """Returns an AST for the schema and a type_lookup dictionary.
  
  Used for code gen and metaprogramming.

  Note: I think app_types is only used for dynamic type checking in
  asdl/py_meta.py.  I guess it could be used for pretty-printing, but that uses
  the actual value and not the type.

  TODO: We should change pretty-printing to also verify the types!
  """
  p = ASDLParser()
  schema_ast = p.parse(f)
  if verbose:
    import sys
    schema_ast.Print(sys.stdout, 0)

  v = Check()
  v.visit(schema_ast)

  if v.errors:
    raise AssertionError('ASDL file is invalid: %s' % v.errors)

  type_lookup = _MakeReflection(schema_ast, app_types)
  return schema_ast, type_lookup
