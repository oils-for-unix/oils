#-------------------------------------------------------------------------------
# Parser for ASDL [1] definition files. Reads in an ASDL description and parses
# it into an AST that describes it.
#
# The EBNF we're parsing here: Figure 1 of the paper [1]. Extended to support
# modules and attributes after a product. Words starting with Capital letters
# are terminals. Literal tokens are in "double quotes". Others are
# non-terminals. Id is either TokenId or ConstructorId.
#
# module        ::= "module" Id "{" [definitions] "}"
# definitions   ::= { TypeId "=" type }
# type          ::= product | sum
# product       ::= fields ["attributes" fields]
# fields        ::= "(" { field, "," } field ")"
# field         ::= TypeId ["?" | "*"] [Id]
# sum           ::= constructor { "|" constructor } ["attributes" fields]
# constructor   ::= ConstructorId [fields]
#
# [1] "The Zephyr Abstract Syntax Description Language" by Wang, et. al. See
#     http://asdl.sourceforge.net/
#-------------------------------------------------------------------------------
from __future__ import print_function

import cStringIO
import re

__all__ = [
    'builtin_types', 'parse', 'AST', 'Module', 'Type', 'Constructor',
    'Field', 'Sum', 'Product', 'VisitorBase', 'Check', 'check',
    'is_simple']


# PATCH: Moved this function from asdl_c.py.
def is_simple(sum):
  """Return True if a sum is a simple.

    A sum is simple if its types have no fields, e.g.
    unaryop = Invert | Not | UAdd | USub
    """
  for t in sum.types:
    if t.fields:
      return False
  return True


class StrType(object):
  def __repr__(self):
    return '<Str>'

class IntType(object):
  def __repr__(self):
    return '<Int>'

class BoolType(object):
  def __repr__(self):
    return '<Bool>'


class ArrayType(object):
  def __init__(self, desc):
    self.desc = desc

  def __repr__(self):
    return '<Array %s>' % self.desc

class MaybeType(object):
  def __init__(self, desc):
    self.desc = desc  # another descriptor

  def __repr__(self):
    return '<Maybe %s>' % self.desc

class UserType(object):
  def __init__(self, typ):
    assert isinstance(typ, type), typ
    self.typ = typ

  def __repr__(self):
    return '<UserType %s>' % self.typ


class TypeLookup(object):
  """Look up types by name.

  The names in a flat namespace.
  """

  def __init__(self, module, app_types=None):
    # types that fields are declared with: int, id, word_part, etc.
    # Fields are not declared with constructor names.
    self.declared_types = {}

    for d in module.dfns:
      self.declared_types[d.name] = d.value

    if app_types is not None:
      self.declared_types.update(app_types)

    # Primitive types.
    self.declared_types['string'] = StrType()
    self.declared_types['int'] = IntType()
    self.declared_types['bool'] = BoolType()

    # Types with fields that need to be reflected on: Product and Constructor.
    self.compound_types = {}
    for d in module.dfns:
      typ = d.value
      if isinstance(typ, Product):
        self.compound_types[d.name] = typ
      elif isinstance(typ, Sum):
        # e.g. 'assign_op' is simple, or 'bracket_op' is not simple.
        self.compound_types[d.name] = typ

        for cons in typ.types:
          self.compound_types[cons.name] = cons

  def ByFieldInstance(self, field):
    """
    Args:
      field: Field() instance
    """
    t = self.declared_types[field.type]
    if field.seq:
      return ArrayType(t)

    if field.opt:
      return MaybeType(t)

    return t

  def ByTypeName(self, type_name):
    """
    Args:
      type_name: string, e.g. 'word_part' or 'LiteralPart'
    """
    if not type_name in self.compound_types:
      print('FATAL: %s' % self.compound_types.keys())
    return self.compound_types[type_name]

  def __repr__(self):
    return repr(self.declared_types)


def _CheckFieldsAndWire(typ, type_lookup):
  for f in typ.fields:
    # Will fail if it doesn't exist
    _ = type_lookup.ByFieldInstance(f)
  typ.type_lookup = type_lookup  # wire it for lookup


def ResolveTypes(module, app_types=None):
  # Walk the module, checking types, and adding the type_lookup attribute
  # everywhere.
  type_lookup = TypeLookup(module, app_types=app_types)

  for node in module.dfns:
    assert isinstance(node, Type), node
    v = node.value
    if isinstance(v, Product):
      _CheckFieldsAndWire(v, type_lookup)

    elif isinstance(v, Sum):
      for cons in v.types:
        _CheckFieldsAndWire(cons, type_lookup)

    else:
      raise AssertionError(v)

  return type_lookup


# The following classes define nodes into which the ASDL description is parsed.
# Note: this is a "meta-AST". ASDL files (such as Python.asdl) describe the AST
# structure used by a programming language. But ASDL files themselves need to be
# parsed. This module parses ASDL files and uses a simple AST to represent them.
# See the EBNF at the top of the file to understand the logical connection
# between the various node types.

builtin_types = {'string', 'int', 'bool'}

class AST(object):
    def Print(self, f, indent):
        raise NotImplementedError

    def __repr__(self):
        f = cStringIO.StringIO()
        self.Print(f, 0)
        return f.getvalue()


class Module(AST):
    def __init__(self, name, dfns):
        self.name = name
        self.dfns = dfns

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sModule %s {\n' % (ind, self.name))

        for d in self.dfns:
          d.Print(f, indent+1)
          f.write('\n')
        f.write('%s}\n' % ind)


class Type(AST):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sType %s {\n' % (ind, self.name))
        self.value.Print(f, indent+1)
        f.write('%s}\n' % ind)



class _CompoundType(AST):
    """Either a Product or Constructor.
    
    encode.py and format.py need a reflection API.
    """

    def __init__(self, fields):
        self.fields = fields or []

        # Add fake spids field.
        # TODO: Only do this if 'attributes' are set.
        if self.fields:
          self.fields.append(Field('int', 'spids', seq=True))

        self.field_lookup = {f.name: f for f in self.fields}
        self.type_lookup = None  # set by ResolveTypes()

        self.type_cache = {}

    def GetFieldNames(self):
        for f in self.fields:
          yield f.name

    def GetFields(self):
        for f in self.fields:
          field_name = f.name
          yield field_name, self.LookupFieldType(field_name)

    def LookupFieldType(self, field_name):
        # Cache and return it.  We don't want to create new instances every
        # time we iterate over the fields.
        try:
          return self.type_cache[field_name]
        except KeyError:
          field = self.field_lookup[field_name]
          desc = self.type_lookup.ByFieldInstance(field)
          self.type_cache[field_name] = desc
          return desc


class Constructor(_CompoundType):
    def __init__(self, name, fields=None):
        _CompoundType.__init__(self, fields)
        self.name = name

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sConstructor %s' % (ind, self.name))

        if self.fields:
          f.write(' {\n')
          for field in self.fields:
            field.Print(f, indent+1)
          f.write('%s}' % ind)

        f.write('\n')


class Field(AST):
    def __init__(self, type, name=None, seq=False, opt=False):
        self.type = type
        self.name = name
        self.seq = seq
        self.opt = opt

    def Print(self, f, indent):
        extra = []
        if self.seq:
            extra.append('seq=True')
        elif self.opt:
            extra.append('opt=True')
        else:
            extra = ""

        ind = indent * '  '
        f.write('%sField %s %s' % (ind, self.name, self.type))
        if extra:
          f.write(' (')
          f.write(', '.join(extra))
          f.write(')')
        f.write('\n')


class Sum(AST):
    def __init__(self, types, attributes=None):
        self.types = types  # List[Constructor]
        self.attributes = attributes or []

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sSum {\n' % ind)
        for t in self.types:
          t.Print(f, indent+1)
        if self.attributes:
          f.write('%s\n' % self.attributes)
        f.write('%s}\n' % ind)


class Product(_CompoundType):
    def __init__(self, fields, attributes=None):
        _CompoundType.__init__(self, fields)
        self.attributes = attributes or []

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sProduct {\n' % ind)
        for field in self.fields:
          field.Print(f, indent+1)
        if self.attributes:
          f.write('%s\n' % self.attributes)
        f.write('%s}\n' % ind)

# A generic visitor for the meta-AST that describes ASDL. This can be used by
# emitters. Note that this visitor does not provide a generic visit method, so a
# subclass needs to define visit methods from visitModule to as deep as the
# interesting node.
# We also define a Check visitor that makes sure the parsed ASDL is well-formed.

class VisitorBase(object):
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

class Check(VisitorBase):
    """A visitor that checks a parsed ASDL tree for correctness.

    Errors are printed and accumulated.
    """
    def __init__(self):
        super(Check, self).__init__()
        self.cons = {}
        self.errors = 0
        self.types = {}  # list of declared field types

    def visitModule(self, mod):
        for dfn in mod.dfns:
            self.visit(dfn)

    def visitType(self, type):
        self.visit(type.value, str(type.name))

    def visitSum(self, sum, name):
        for t in sum.types:
            # Simple sum types can't conflict
            if is_simple(sum):
                continue
            self.visit(t, name)

    def visitConstructor(self, cons, name):
        key = str(cons.name)
        conflict = self.cons.get(key)
        if conflict is None:
            self.cons[key] = name
        else:
            # Problem: This assumes a flat namespace, which we don't want!
            # This check is more evidence that a flat namespace isn't
            # desirable.
            print('Redefinition of constructor {}'.format(key))
            print('Defined in {} and {}'.format(conflict, name))
            self.errors += 1
        for f in cons.fields:
            self.visit(f, key)

    def visitField(self, field, name):
        key = str(field.type)
        l = self.types.setdefault(key, [])
        l.append(name)

    def visitProduct(self, prod, name):
        for f in prod.fields:
            self.visit(f, name)

def check(mod, app_types=None):
    """Check the parsed ASDL tree for correctness.

    Return True if success. For failure, the errors are printed out and False
    is returned.
    """
    app_types = app_types or {}
    v = Check()
    v.visit(mod)
    return not v.errors

# The ASDL parser itself comes next. The only interesting external interface
# here is the top-level parse function.

def parse(f):
    """Parse ASDL from the given file and return a Module node describing it."""
    parser = ASDLParser()
    return parser.parse(f)

# Types for describing tokens in an ASDL specification.
class TokenKind:
    """TokenKind is provides a scope for enumerated token kinds."""
    (ConstructorId, TypeId, Equals, Comma, Question, Pipe, Asterisk,
     LParen, RParen, LBrace, RBrace) = range(11)

    operator_table = {
        '=': Equals, ',': Comma,    '?': Question, '|': Pipe,    '(': LParen,
        ')': RParen, '*': Asterisk, '{': LBrace,   '}': RBrace}

class Token:
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

def tokenize_asdl(f):
    """Tokenize the given buffer. Yield Token objects."""
    for lineno, line in enumerate(f, 1):
        for m in re.finditer(r'\s*(\w+|--.*|.)', line.strip()):
            c = m.group(1)
            if c[0].isalpha():
                # Some kind of identifier
                if c[0].isupper():
                    yield Token(TokenKind.ConstructorId, c, lineno)
                else:
                    yield Token(TokenKind.TypeId, c, lineno)
            elif c[:2] == '--':
                # Comment
                break
            else:
                # Operators
                try:
                    op_kind = TokenKind.operator_table[c]
                except KeyError:
                    raise ASDLSyntaxError('Invalid operator %s' % c, lineno)
                yield Token(op_kind, c, lineno)

class ASDLParser:
    """Parser for ASDL files.

    Create, then call the parse method on a buffer containing ASDL.
    This is a simple recursive descent parser that uses tokenize_asdl for the
    lexing.
    """
    def __init__(self):
        self._tokenizer = None
        self.cur_token = None

    def parse(self, f):
        """Parse the ASDL in the file and return an AST with a Module root.
        """
        self._tokenizer = tokenize_asdl(f)
        self._advance()
        return self._parse_module()

    def _parse_module(self):
        if self._at_keyword('module'):
            self._advance()
        else:
            raise ASDLSyntaxError(
                'Expected "module" (found {})'.format(self.cur_token.value),
                self.cur_token.lineno)
        name = self._match(self._id_kinds)
        self._match(TokenKind.LBrace)
        defs = self._parse_definitions()
        self._match(TokenKind.RBrace)
        return Module(name, defs)

    def _parse_definitions(self):
        defs = []
        while self.cur_token.kind == TokenKind.TypeId:
            typename = self._advance()
            self._match(TokenKind.Equals)
            type = self._parse_type()
            defs.append(Type(typename, type))
        return defs

    def _parse_type(self):
        if self.cur_token.kind == TokenKind.LParen:
            # If we see a (, it's a product
            return self._parse_product()
        else:
            # Otherwise it's a sum. Look for ConstructorId
            sumlist = [Constructor(self._match(TokenKind.ConstructorId),
                                   self._parse_optional_fields())]
            while self.cur_token.kind == TokenKind.Pipe:
                # More constructors
                self._advance()
                sumlist.append(Constructor(
                                self._match(TokenKind.ConstructorId),
                                self._parse_optional_fields()))
            return Sum(sumlist, self._parse_optional_attributes())

    def _parse_product(self):
        return Product(self._parse_fields(), self._parse_optional_attributes())

    def _parse_fields(self):
        fields = []
        self._match(TokenKind.LParen)
        while self.cur_token.kind == TokenKind.TypeId:
            typename = self._advance()
            is_seq, is_opt = self._parse_optional_field_quantifier()
            id = (self._advance() if self.cur_token.kind in self._id_kinds
                                  else None)
            fields.append(Field(typename, id, seq=is_seq, opt=is_opt))
            if self.cur_token.kind == TokenKind.RParen:
                break
            elif self.cur_token.kind == TokenKind.Comma:
                self._advance()
        self._match(TokenKind.RParen)
        return fields

    def _parse_optional_fields(self):
        if self.cur_token.kind == TokenKind.LParen:
            return self._parse_fields()
        else:
            return None

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

    _id_kinds = (TokenKind.ConstructorId, TokenKind.TypeId)

    def _match(self, kind):
        """The 'match' primitive of RD parsers.

        * Verifies that the current token is of the given kind (kind can
          be a tuple, in which the kind must match one of its members).
        * Returns the value of the current token
        * Reads in the next token
        """
        if (isinstance(kind, tuple) and self.cur_token.kind in kind or
            self.cur_token.kind == kind
            ):
            value = self.cur_token.value
            self._advance()
            return value
        else:
            raise ASDLSyntaxError(
                'Unmatched {} (found {})'.format(kind, self.cur_token.kind),
                self.cur_token.lineno)

    def _at_keyword(self, keyword):
        return (self.cur_token.kind == TokenKind.TypeId and
                self.cur_token.value == keyword)


def LoadSchema(f, app_types):
  """Parse an ASDL schema.  Used for code gen and metaprogramming."""
  asdl_module = parse(f)

  if not check(asdl_module, app_types):
    raise AssertionError('ASDL file is invalid')

  type_lookup = ResolveTypes(asdl_module, app_types)
  return asdl_module, type_lookup
