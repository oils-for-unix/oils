"""front_end.py: Lexer and parser for the ASDL schema language."""
from __future__ import print_function

import re

from asdl import ast
from asdl.ast import (AST, Use, Module, TypeDecl, Constructor, Field, Sum,
                      SimpleSum, Product)
from asdl.util import log

_ = log

_KEYWORDS = ['use', 'module', 'generate']

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

    # Oil addition for parameterized types.
    ('LBracket', '['),
    ('RBracket', ']'),

    # - Start with Dict[string, bool].
    # - List[string] is an alias for string*
    #
    # statically typed: Dict and List
    # dynamically typed: dict and list
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
    """Tokenize the given buffer.

    Yield Token objects.
    """
    for lineno, line in enumerate(f, 1):
        for m in re.finditer(r'\s*(\w+|--.*|#.*|.)', line.strip()):
            c = m.group(1)
            if c in _KEYWORDS:
                yield Token(TokenKind.Keyword, c, lineno)

            elif c[0].isalpha():
                yield Token(TokenKind.Name, c, lineno)

            elif c.startswith('--') or c.startswith('#'):
                # ASDL comments start with --
                # Added # comments like Python and shell
                break

            else:
                # Operators
                try:
                    op_kind = _TOKEN_INT[c]
                except KeyError:
                    raise ASDLSyntaxError('Invalid operator %s' % c, lineno)
                yield Token(op_kind, c, lineno)


def _SumIsSimple(variant_list):
    """Return True if a sum is a simple.

    A sum is simple if its types have no fields, e.g. unaryop = Invert |
    Not | UAdd | USub
    """
    for t in variant_list:
        if t.fields or t.shared_type:
            return False
    return True


_CODE_GEN_OPTIONS = [
    'no_namespace_suffix',  # Id.Foo instead of Id_e.Foo
    'integers',  # integer builtin_i instead of strongly typed builtin_e
    'bit_set',  # not implemented: 1 << n instead of n

    # probably don't need this
    # 'common_synthetic_field:left_tok',

    # Put this type, and transitive closure of types it references, in the
    # unique "first class variant" namespace, and generate type reflection.
    'reflect_all_types',

    # Squeeze and Freeze, with the number of bits as a option Hm the headers
    # here still need type reflection.  Probably OK.
    'mirror_all_types:16',
]


class ASDLParser(object):
    """Parser for ASDL files.

    Create, then call the parse method on a buffer containing ASDL. This
    is a simple recursive descent parser that uses _Tokenize for the
    lexing.
    """

    def __init__(self):
        self._tokenizer = None
        self.cur_token = None

    def parse(self, f):
        """Parse the ASDL in the file and return an AST with a Module root."""
        self._tokenizer = _Tokenize(f)
        self._advance()
        return self._parse_module()

    def _parse_module(self):
        """
    type_decl  : NAME (':' NAME) '=' compound_type
    module     : 'module' NAME '{' use* type_decl* '}'

    We added:
      : for code gen options
      use for imports

    alloc_members =
      List
    | Dict
    | Struct
    generate [bit_set]
    
    -- color::Red, not color_e::Red or color_i::Red
    color = Red | Green
            generate [integers, no_sum_suffix]
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
            type_ = self._parse_compound_type()
            defs.append(TypeDecl(typename, type_))

        self._match(TokenKind.RBrace)
        return Module(name, uses, defs)

    def _parse_use(self):
        """Use: 'use' NAME+ '{' NAME+ '}'.

        example: use frontend syntax { Token }

        This means frontend/syntax.asdl.h :: Token
        """
        self._advance()  # past 'use'
        module_parts = []
        while self.cur_token.kind == TokenKind.Name:
            part = self._advance()
            module_parts.append(part)

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
        #print('MOD %s' % module_parts)
        return Use(module_parts, type_names)

    def _parse_compound_type(self):
        """Constructor : NAME fields? | NAME '%' NAME  # shared variant.

        compound_type : product
                      | constructor ('|' constructor)*
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
            generate = self._parse_optional_generate()

            # Additional validation
            if generate is not None:
                for g in generate:
                    if g not in _CODE_GEN_OPTIONS:
                        raise ASDLSyntaxError('Invalid code gen option %r' % g,
                                              self.cur_token.lineno)

            if _SumIsSimple(sumlist):
                return SimpleSum(sumlist, generate)
            else:
                return Sum(sumlist, generate)

    def _parse_type_expr(self):
        """One or two params:

        type_params : '[' type_expr ( ',' type_expr )* ']'

        type_expr   : NAME type_params? (''?' | '*')?  # allow one suffix

        NAME is validated against Optional, List, Dict afterward
        """
        type_name = self._match(TokenKind.Name)

        # Accept Python-like naming!
        if type_name == 'str':
            type_name = 'string'

        children = []
        if self.cur_token.kind == TokenKind.LBracket:
            self._advance()
            children.append(self._parse_type_expr())
            if self.cur_token.kind == TokenKind.Comma:
                self._advance()
                children.append(self._parse_type_expr())

            self._match(TokenKind.RBracket)

        if type_name in ('List', 'Optional'):
            if len(children) != 1:
                raise ASDLSyntaxError(
                    'Expected 1 type param to {}'.format(type_name),
                    self.cur_token.lineno)
        elif type_name == 'Dict':
            if len(children) != 2:
                raise ASDLSyntaxError(
                    'Expected 2 type params to {}'.format(type_name),
                    self.cur_token.lineno)
        else:
            if len(children) != 0:
                raise ASDLSyntaxError(
                    'Expected zero type params to {}'.format(type_name),
                    self.cur_token.lineno)

        if len(children):
            typ = ast.ParameterizedType(type_name, children)
        else:
            typ = ast.NamedType(type_name)

        if self.cur_token.kind == TokenKind.Asterisk:
            # string* is equivalent to List[string]
            typ = ast.ParameterizedType('List', [typ])
            self._advance()

        elif self.cur_token.kind == TokenKind.Question:
            # string* is equivalent to Optional[string]
            typ = ast.ParameterizedType('Optional', [typ])
            self._advance()

        return typ

    def _parse_fields(self):
        """fields_inner: type_expr NAME ( ',' type_expr NAME )* ','?

        fields      : '(' fields_inner? ')'

        Name Quantifier?  should be changed to typename.
        """
        fields = []
        self._match(TokenKind.LParen)
        while self.cur_token.kind == TokenKind.Name:
            typ = self._parse_type_expr()
            field_name = self._match(TokenKind.Name)

            fields.append(Field(typ, field_name))

            if self.cur_token.kind == TokenKind.RParen:
                break
            elif self.cur_token.kind == TokenKind.Comma:
                self._advance()

        self._match(TokenKind.RParen)
        return fields

    def _parse_list(self):
        """list_inner: NAME ( ',' NAME )* ','?

        list      : '[' list_inner? ']'
        """
        generate = []
        self._match(TokenKind.LBracket)
        while self.cur_token.kind == TokenKind.Name:
            name = self._match(TokenKind.Name)

            generate.append(name)

            if self.cur_token.kind == TokenKind.RBracket:
                break
            elif self.cur_token.kind == TokenKind.Comma:
                self._advance()

        self._match(TokenKind.RBracket)
        return generate

    def _parse_optional_generate(self):
        """Attributes = 'generate' list."""
        if self._at_keyword('generate'):
            self._advance()
            return self._parse_list()
        else:
            return None

    def _parse_product(self):
        """Product: fields attributes?"""
        return Product(self._parse_fields())

    def _advance(self):
        """Return current token; read next token into self.cur_token."""
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


_PRIMITIVE_TYPES = [
    'string',
    'int',
    'float',
    'bool',

    # 'any' is used:
    # - for value.Obj in the the Oil expression evaluator.  We're not doing any
    #   dynamic or static checking now.
    'any',
]


def _ResolveType(typ, type_lookup):
    # type: (AST, dict) -> None
    """Recursively attach a 'resolved' field to AST nodes."""
    if isinstance(typ, ast.NamedType):
        if typ.name not in _PRIMITIVE_TYPES:
            ast_node = type_lookup.get(typ.name)
            if ast_node is None:
                raise ASDLSyntaxError("Couldn't find type %r" % typ.name)
            typ.resolved = ast_node

    elif isinstance(typ, ast.ParameterizedType):
        for child in typ.children:
            _ResolveType(child, type_lookup)

        if typ.type_name == 'Optional':
            child = typ.children[0]
            if isinstance(child, ast.NamedType):
                if child.name in _PRIMITIVE_TYPES and child.name != 'string':
                    raise ASDLSyntaxError(
                        'Optional primitive type {} not allowed'.format(
                            child.name))

                if child.resolved and isinstance(child.resolved,
                                                 ast.SimpleSum):
                    raise ASDLSyntaxError(
                        'Optional simple sum type {} not allowed'.format(
                            child.name))

    else:
        raise AssertionError()


def _ResolveFields(field_ast_nodes, type_lookup):
    """
  Args:
    type_lookup: Populated by name resolution
  """
    for field in field_ast_nodes:
        _ResolveType(field.typ, type_lookup)


def _ResolveModule(module, app_types):
    """Name resolution for NamedType."""
    # Types that fields are declared with: int, id, word_part, etc.
    # Fields are NOT declared with Constructor names.
    type_lookup = dict(app_types)

    # Note: we don't actually load the type, and instead leave that to MyPy /
    # C++.  A consequence of this is TypeNameHeuristic().
    for u in module.uses:
        for type_name in u.type_names:
            type_lookup[type_name] = u  # type: ast.Use()

    # NOTE: We need two passes because types can be mutually recursive, e.g.
    # asdl/arith.asdl.

    # First pass: collect declared types and make entries for them.
    for d in module.dfns:
        type_lookup[d.name] = d.value

    # Second pass: add NamedType.resolved field
    for d in module.dfns:
        ast_node = d.value
        if isinstance(ast_node, ast.Product):
            #log('fields %s', ast_node.fields)
            _ResolveFields(ast_node.fields, type_lookup)

        elif isinstance(ast_node, ast.Sum):
            for cons in ast_node.types:
                _ResolveFields(cons.fields, type_lookup)

        else:
            raise AssertionError(ast_node)


def LoadSchema(f, app_types, verbose=False):
    """Returns an AST for the schema."""
    p = ASDLParser()
    schema_ast = p.parse(f)
    if verbose:
        import sys
        schema_ast.Print(sys.stdout, 0)

    # Make sure all the names are valid
    _ResolveModule(schema_ast, app_types)
    return schema_ast
