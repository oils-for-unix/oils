#!/usr/bin/env python2
"""Lex_gen.py."""
from __future__ import print_function

from _devbuild.gen.id_kind import (TEST_UNARY_LOOKUP, TEST_BINARY_LOOKUP,
                                   TEST_OTHER_LOOKUP)
from _devbuild.gen.id_kind_asdl import Id_str
from _devbuild.gen.types_asdl import lex_mode_str

import cStringIO
import sys
import sre_parse
import sre_constants

from frontend import lexer_def


def PrintTree(re_tree, depth=2):
    """
  re_tree: List of children
  """
    for child in re_tree:
        name, arg = child
        sys.stdout.write(depth * '\t')
        sys.stdout.write(name)
        sys.stdout.write(' ')
        if name == 'in':  # character class
            print('{')
            PrintTree(arg, depth=depth + 1)
            sys.stdout.write(depth * '\t')
            print('}')
        elif name == 'max_repeat':  # repetition
            min_, max_, children = arg
            # min = 0 means *, min = 1 means +
            assert min_ in (0, 1), min_
            print(min_, max_, '{')
            PrintTree(children, depth=depth + 1)
            sys.stdout.write(depth * '\t')
            print()
        elif name == 'negate':  # Oh this is a ^.  It doesn't form a node.
            assert arg is None
            print()
        elif name == 'literal':  # Quote \ and " in re2c syntax
            print(repr(chr(arg)))
        elif name == 'not_literal':  # ditto
            print(repr(chr(arg)))
        elif name == 'range':  # ascii range
            begin, end = arg
            print(repr(chr(begin)), repr(chr(end)))
        elif name == 'any':  # This is the '.' character
            assert arg is None
            print()
        else:
            raise AssertionError(name)

    # NOTE: negate and not_literal are sort of duplicated


def PrintRegex(pat):
    re_tree = sre_parse.parse(pat)
    print('\t\t[')
    PrintTree(re_tree)
    print('\t\t]')


# re2c literals are inside double quotes, so we need to escape \ and "
# But we don't need to do anything with the quoted literal ^
LITERAL_META = ['\\', '"']
LITERAL_META_CODES = [ord(c) for c in LITERAL_META]


def _Literal(arg, char_escapes=LITERAL_META_CODES):
    if arg == ord('\n'):
        s = r'\n'
    elif arg == ord('\r'):
        s = r'\r'
    elif arg == ord('\t'):
        s = r'\t'
    elif arg >= 0x80 or arg < 0x20:  # 0x1f and below
        s = '\\x%02x' % arg  # for \x80-\xff
    elif arg in char_escapes:
        s = '\\' + chr(arg)
    else:
        s = chr(arg)
    return s


# - means range.  Note that re2c gives an error we uselessly escape \^.
CHAR_CLASS_META = ['\\', '-', ']']
CHAR_CLASS_META_CODES = [ord(c) for c in CHAR_CLASS_META]


def _CharClassLiteral(arg):
    return _Literal(arg, char_escapes=CHAR_CLASS_META_CODES)


def TranslateConstant(pat):
    return '"' + ''.join(_Literal(ord(c)) for c in pat) + '"'


def TranslateTree(re_tree, f, in_char_class=False):
    """
  re_tree: List of children
  """
    for child in re_tree:
        name, arg = child
        if name == 'in':  # character class
            f.write('[')
            TranslateTree(arg, f,
                          in_char_class=True)  # list of literals/ranges
            f.write(']')

        elif name == 'branch':  # |
            _, branches = arg
            for i, branch in enumerate(branches):
                if i != 0:
                    f.write(' | ')
                TranslateTree(branch, f)

        elif name == 'max_repeat':  # repetition
            min_, max_, children = arg
            # min = 0 means *, min = 1 means +
            #assert min_ in (0, 1), min_
            TranslateTree(children, f)

            if min_ == 0 and max_ == 1:
                f.write('? ')

            elif max_ == sre_constants.MAXREPEAT:
                if min_ == 0:
                    f.write('* ')
                elif min_ == 1:
                    f.write('+ ')
                else:
                    assert 0, min_

            else:  # re2c also supports [0-7]{1,2} syntax
                # note: might generated {2,2}
                f.write('{%d,%d} ' % (min_, max_))

        elif name == 'negate':  # ^ in [^a-z]
            assert arg is None
            f.write('^')

        elif name == 'literal':  # Quote \ and " in re2c syntax
            # TODO: it matters if we're inside a character class
            #print("literal ARG %r" % arg)

            if in_char_class:
                s = _CharClassLiteral(arg)
            else:
                s = '"%s" ' % _Literal(arg)
            f.write(s)

        elif name == 'not_literal':  # ditto
            assert not in_char_class
            f.write('[^%s]' % _CharClassLiteral(arg))

        elif name == 'range':  # ascii range
            begin, end = arg
            f.write('%s-%s' %
                    (_CharClassLiteral(begin), _CharClassLiteral(end)))

        elif name == 'any':  # This is the '.' character
            assert arg is None
            f.write('.')

        elif name == 'subpattern':
            _, children = arg  # Not sure what the _ is, but it works
            f.write('(')
            TranslateTree(children, f)
            f.write(')')

        else:
            if 0:
                from mycpp.mylib import log
                log('child %s', child)
            raise RuntimeError("I don't understand regex construct: %r" % name)

    # NOTE: negate and not_literal are sort of duplicated


def TranslateRegex(pat):
    re_tree = sre_parse.parse(pat)
    # For debugging
    #import pprint
    #print(pprint.pformat(re_tree), file=sys.stderr)
    f = cStringIO.StringIO()
    try:
        TranslateTree(re_tree, f)
    except RuntimeError:
        print('Error translating %r' % pat, file=sys.stderr)
        raise
    return f.getvalue()


# This explains the sentinel method, which we will use.
# http://re2c.org/examples/example_01.html
#
# TODO: Change ParseTuple to use 's' rather than '#s' ?

# I don't think we need this YYFILL mechanism, because we lex a line at a
# time.
# http://re2c.org/examples/example_03.html


def TranslateSimpleLexer(func_name, lexer_def):
    print(r"""
static inline void %s(const unsigned char* line, int line_len,
    int start_pos, int* id, int* end_pos) {
  assert(start_pos <= line_len);  /* caller should have checked */

  const unsigned char* p = line + start_pos;  /* modified by re2c */

  /* Echo and History lexer apparently need this, but others don't */
  __attribute__((unused)) const unsigned char* YYMARKER;

  for (;;) {
    /*!re2c
""" % func_name)

    for is_regex, pat, id_ in lexer_def:
        if is_regex:
            re2c_pat = TranslateRegex(pat)
        else:
            re2c_pat = TranslateConstant(pat)
        id_name = Id_str(id_).split('.')[-1]  # e.g. Undefined_Tok
        print('      %-30s { *id = id__%s; break; }' % (re2c_pat, id_name))

    # EARLY RETURN: Do NOT advance past the NUL terminator.
    print('      %-30s { *id = id__Eol_Tok; *end_pos = start_pos; return; }' % \
        r'"\x00"')

    print("""
    */
  }
  *end_pos = p - line;  /* relative */
}
""")


def TranslateBracket(func_name, token_dict):
    print(r"""
static inline int %s(const unsigned char* s, int len) {
  const unsigned char* p = s;  /* modified by re2c */
  const unsigned char* end = s + len;

  __attribute__((unused)) const unsigned char* YYMARKER;
  int id;

  for (;;) {
    /*!re2c
""" % func_name)

    for pat in sorted(token_dict):
        id_ = token_dict[pat]
        re2c_pat = TranslateConstant(pat)
        id_name = Id_str(id_).split('.')[-1]  # e.g. Undefined_Tok
        print('      %-30s { id = id__%s; break; }' % (re2c_pat, id_name))

    # EARLY RETURN: Do NOT advance past other chars, including the NUL
    # terminator.
    print('      %-30s { return id__Undefined_Tok; }' % '*')

    print("""
    */
  }
  // must be an exact match
  return (p == end) ? id : id__Undefined_Tok;
}
""")


def StringToInt(func_name, name_def):
    print(r"""
static inline void %s(const unsigned char* s, int len, int* id) {
  const unsigned char* p = s;  /* modified by re2c */
  const unsigned char* end = s + len;

  //fprintf(stderr, "*** s = %%s\n", s);

  for (;;) {
    /*!re2c
""" % func_name)

    for name, enum in name_def:
        re2c_pat = TranslateConstant(name)
        print('      %-30s { *id = %s; break; }' % (re2c_pat, enum))

    # Not found.  * matches anything else.
    print('      %-30s { *id = 0; return; }' % \
        r'*')

    print(r"""
    */
  }
  if (p != end) {
    //fprintf(stderr, "EXTRA CHARS\n", s);
    *id = 0;  // Not an exact match
  }
}
""")

    # TODO: Check that we're at the END OF THE STRING


def TranslateOshLexer(lexer_def):
    # https://stackoverflow.com/questions/12836171/difference-between-an-inline-function-and-static-inline-function
    # Has to be 'static inline' rather than 'inline', otherwise the
    # _bin/oil.ovm-dbg build fails (but the _bin/oil.ovm doesn't!).
    # Since we reference this function in exactly one translation unit --
    # fastlex.c, the difference is moot, and we just satisfy the compiler.

    print(r"""
/* Common stuff */

/*!re2c
  re2c:define:YYCTYPE = "unsigned char";
  re2c:define:YYCURSOR = p;
  re2c:yyfill:enable = 0;  // generated code doesn't ask for more input
*/

static inline void MatchOshToken(int lex_mode, const unsigned char* line, int line_len,
                              int start_pos, int* id, int* end_pos) {
  assert(start_pos <= line_len);  /* caller should have checked */

  const unsigned char* p = line + start_pos;  /* modified by re2c */
  //printf("p: %p q: %p\n", p, q);

  __attribute__((unused)) const unsigned char* YYMARKER;  /* why do we need this? */
  switch (lex_mode)  {
""")

    # TODO: Should be ordered by most common?  Or will profile-directed feedback
    # help?
    for state, pat_list in lexer_def.iteritems():
        # e.g. lex_mode.DQ => lex_mode__DQ
        print('  case %s:' % lex_mode_str(state).replace('.', '__'))
        print('    for (;;) {')
        print('      /*!re2c')

        for is_regex, pat, id_ in pat_list:
            if is_regex:
                re2c_pat = TranslateRegex(pat)
            else:
                re2c_pat = TranslateConstant(pat)
            id_name = Id_str(id_).split('.')[-1]  # e.g. Undefined_Tok
            print('      %-30s { *id = id__%s; break; }' % (re2c_pat, id_name))

        # EARLY RETURN: Do NOT advance past the NUL terminator.
        print('      %-30s { *id = id__Eol_Tok; *end_pos = start_pos; return; }' % \
            r'"\x00"')

        print('      */')
        print('    }')
        print('    break;')
        print()

    # This is literal code without generation:
    """
  case lex_mode__OUTER:
    for (;;) {
      /*!re2c
      literal_chunk = [a-zA-Z0-9_/.-]+;
      var_like    = [a-zA-Z_][a-zA-Z0-9_]* "=";  // might be NAME=val
      comment     = [ \t\r]* "#" [^\000\r\n]*;
      space       = [ \t\r]+;
      nul = "\000";

      literal_chunk { *id = id__Lit_Chars; break; }
      var_like      { *id = id__Lit_VarLike; break; }

      [ \t\r]* "\n" { *id = id__Op_Newline; break; }
      space         { *id = id__WS_Space; break; }

      nul           { *id = id__Eof_Real; break; }

      // anything else
      *             { *id = id__Lit_Other; break; }

      */
    }

    *end_pos = p - line;
    break;

  case lex_mode__COMMENT:
    *id = id__Lit_Other;
    *end_pos = 6;
    break;
  """

    print("""\
  default:
    assert(0);

  }
  *end_pos = p - line;  /* relative */
}
""")


def TranslateRegexToPredicate(py_regex, func_name):
    re2c_pat = TranslateRegex(py_regex)
    print(r"""
static inline int %s(const unsigned char* s, int len) {
  const unsigned char* p = s;  /* modified by re2c */
  const unsigned char* end = s + len;

  /* MatchBraceRangeToken needs this, but others don't */
  __attribute__((unused)) const unsigned char* YYMARKER;

  /*!re2c
  re2c:define:YYCTYPE = "unsigned char";
  re2c:define:YYCURSOR = p;
  %-30s { return p == end; }  // Match must be anchored right, like $
  *     { return 0; }
  */
}
""" % (func_name, re2c_pat))


    # note: use YYCURSOR and YYLIMIT
    # limit should be the end of string
    # line + line_len
def main(argv):
    action = argv[1]
    if action == 'c':
        # Code is printed to stdout

        TranslateOshLexer(lexer_def.LEXER_DEF)

        TranslateSimpleLexer('MatchEchoToken', lexer_def.ECHO_E_DEF)
        TranslateSimpleLexer('MatchGlobToken', lexer_def.GLOB_DEF)
        TranslateSimpleLexer('MatchPS1Token', lexer_def.PS1_DEF)
        TranslateSimpleLexer('MatchHistoryToken', lexer_def.HISTORY_DEF)
        TranslateSimpleLexer('MatchBraceRangeToken', lexer_def.BRACE_RANGE_DEF)
        TranslateSimpleLexer('MatchJ8Token', lexer_def.J8_DEF)
        TranslateSimpleLexer('MatchJ8LinesToken', lexer_def.J8_LINES_DEF)
        TranslateSimpleLexer('MatchJ8StrToken', lexer_def.J8_STR_DEF)
        TranslateSimpleLexer('MatchJsonStrToken', lexer_def.JSON_STR_DEF)
        TranslateSimpleLexer('MatchShNumberToken', lexer_def.SH_NUMBER_DEF)

        TranslateRegexToPredicate(lexer_def.VAR_NAME_RE, 'IsValidVarName')
        TranslateRegexToPredicate(lexer_def.SHOULD_HIJACK_RE, 'ShouldHijack')
        TranslateRegexToPredicate(lexer_def.LOOKS_LIKE_INTEGER,
                                  'LooksLikeInteger')
        TranslateRegexToPredicate(lexer_def.LOOKS_LIKE_YSH_INT,
                                  'LooksLikeYshInt')
        TranslateRegexToPredicate(lexer_def.LOOKS_LIKE_YSH_FLOAT,
                                  'LooksLikeYshFloat')

        TranslateBracket('BracketUnary', TEST_UNARY_LOOKUP)
        TranslateBracket('BracketBinary', TEST_BINARY_LOOKUP)
        TranslateBracket('BracketOther', TEST_OTHER_LOOKUP)

    elif action == 'print-all':
        # Top level is a switch statement.
        for state, pat_list in lexer_def.LEXER_DEF.iteritems():
            print(state)
            # This level is re2c patterns.
            for is_regex, pat, token_id in pat_list:
                print('\t%r  ->  %r' % (pat, token_id))
                if is_regex:
                    #print re_tree
                    _ = TranslateRegex(pat)
                    #print out_pat

            print()

    elif action == 'print-regex':
        unique = set()

        num_regexes = 0
        for state, pat_list in lexer_def.LEXER_DEF.iteritems():
            print(state)
            # This level is re2c patterns.
            for is_regex, pat, token_id in pat_list:
                #print '\t%r  ->  %r' % (pat, token_id)
                if is_regex:
                    print('\t' + pat)
                    print('\t' + TranslateRegex(pat))
                    print()
                    #PrintRegex(pat)
                    num_regexes += 1
                    unique.add(pat)
                else:
                    print('\t' + TranslateConstant(pat))

            print()

        print('Printed %d regexes (%d unique)' % (num_regexes, len(unique)))


if __name__ == '__main__':
    try:
        main(sys.argv)
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
