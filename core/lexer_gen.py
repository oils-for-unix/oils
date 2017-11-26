#!/usr/bin/python
"""
lex_gen.py
"""

import cStringIO
import sys
import sre_parse

from osh import lex


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
      print '{'
      PrintTree(arg, depth=depth+1)
      sys.stdout.write(depth * '\t')
      print '}'
    elif name == 'max_repeat':  # repetition
      min_, max_, children = arg
      # min = 0 means *, min = 1 means +
      assert min_ in (0, 1), min_
      print min_, max_, '{'
      PrintTree(children, depth=depth+1)
      sys.stdout.write(depth * '\t')
      print
    elif name == 'negate':  # Oh this is a ^.  It doesn't form a node.
      assert arg is None
      print
    elif name == 'literal':  # Quote \ and " in re2c syntax
      print repr(chr(arg))
    elif name == 'not_literal':  # ditto
      print repr(chr(arg))
    elif name == 'range':  # ascii range
      begin, end = arg
      print repr(chr(begin)), repr(chr(end))
    elif name == 'any':  # This is the '.' character
      assert arg is None
      print
    else:
      raise AssertionError(name)

  # NOTE: negate and not_literal are sort of duplicated


def PrintRegex(pat):
  re_tree = sre_parse.parse(pat)
  print '\t\t['
  PrintTree(re_tree)
  print '\t\t]'


# ^ means negation, - means range
CHAR_CLASS_META = ['\\', '^', '-', ']']
CHAR_CLASS_META_CODES = [ord(c) for c in CHAR_CLASS_META]

# re2c literals are inside double quotes, so we don't need to do anything with
# ^ or whatever.
LITERAL_META = ['\\', '"']
LITERAL_META_CODES = [ord(c) for c in LITERAL_META]


def _CharClassLiteral(arg):
  if arg == 0:
    s = r'\x00'           # "\x00"
  elif arg == ord('\n'):
    s = r'\n' 
  elif arg == ord('\r'):
    s = r'\r' 
  elif arg == ord('\t'):
    s = r'\t' 
  elif arg in CHAR_CLASS_META_CODES:
    s = '\\' + chr(arg)
  else:
    s = chr(arg)
  return s


def _Literal(arg):
  if arg == 0:
    s = r'\x00'           # "\000"
  elif arg == ord('\n'):
    s = r'\n' 
  elif arg == ord('\r'):
    s = r'\r' 
  elif arg == ord('\t'):
    s = r'\t' 
  elif arg in LITERAL_META_CODES:
    s = '\\' + chr(arg)
  else:
    s = chr(arg)
  return s


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
      TranslateTree(arg, f, in_char_class=True)  # list of literals/ranges
      f.write(']')

    elif name == 'max_repeat':  # repetition
      min_, max_, children = arg
      # min = 0 means *, min = 1 means +
      assert min_ in (0, 1), min_
      TranslateTree(children, f)
      if min_ == 0:
        if max_ == 1:
          f.write('? ')
        else:
          f.write('* ')
      elif min_ == 1:
        f.write('+ ')
      else:
        assert 0, min_

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
      f.write('%s-%s' % (chr(begin), chr(end)))

    elif name == 'any':  # This is the '.' character
      assert arg is None
      f.write('.')

    else:
      raise AssertionError(name)

  # NOTE: negate and not_literal are sort of duplicated


def TranslateRegex(pat):
  re_tree = sre_parse.parse(pat)
  f = cStringIO.StringIO()
  TranslateTree(re_tree, f)
  return f.getvalue()


# This explains the sentinel method, which we will use.
# http://re2c.org/examples/example_01.html
#
# TODO: Change ParseTuple to use 's' rather than '#s' ?

# I don't think we need this YYFILL mechanism, because we lex a line at a
# time.
# http://re2c.org/examples/example_03.html


def TranslateLexer(lexer_def):
  print r"""
/* Common stuff */

/*!re2c
  re2c:define:YYCTYPE = "unsigned char";
  re2c:define:YYCURSOR = p;
  re2c:yyfill:enable = 0;  // generated code doesn't ask for more input
*/

inline void MatchToken(int lex_mode, unsigned char* line, int line_len,
                       int start_pos, int* id, int* end_pos) {

  // bounds checking
  if (start_pos >= line_len) {
    fprintf(stderr, "start_pos %d  line_len %d\n", start_pos, line_len);
    assert(0);
  }
  //assert(start_pos < line_len);

  unsigned char* p = line + start_pos;  /* modified by re2c */
  //printf("p: %p q: %p\n", p, q);

  unsigned char* YYMARKER;  /* why do we need this? */
  switch (lex_mode)  {
"""

  # TODO: Should be ordered by most common?

  for state, pat_list in lexer_def.iteritems():
    # HACK: strip off '_e'
    prefix = state.__class__.__name__[:-2]
    print '  case %s__%s:' % (prefix, state.name)
    print '    for (;;) {'
    print '      /*!re2c'

    for is_regex, pat, token_id in pat_list:
      if is_regex:
        re2_pat = TranslateRegex(pat)
      else:
        re2_pat = TranslateConstant(pat)
      # TODO: Remove this after debugging Id problem
      from core import id_kind
      id_name = id_kind.IdName(token_id)
      print '      %-30s { *id = id__%s; break; }' % (re2_pat, id_name)
    print '      %-30s { *id = id__%s; break; }' % (r'"\x00"', 'Eol_Tok')
    print '      */'
    print '    }'
    print '    break;'
    print

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

    //*id = id__Lit_Other;
    *end_pos = p - line;  /* relative */
    break;

  case lex_mode__COMMENT:
    *id = id__Lit_Other;
    *end_pos = 6;
    break;
  """

  print """\
  default:
    assert(0);

  }
  *end_pos = p - line;  /* relative */
}
"""


  # note: use YYCURSOR and YYLIMIT
  # limit should be the end of string
  # line + line_len
def main(argv):
  # This becomes osh-lex.re2c.c.  It is compiled to osh-lex.c and then
  # included.

  action = argv[1]
  if action == 'c':
    TranslateLexer(lex.LEXER_DEF)

  elif action == 'print-all':
    # Top level is a switch statement.
    for state, pat_list in lex.LEXER_DEF.iteritems():
      print state
      # This level is re2c patterns.
      for is_regex, pat, token_id in pat_list:
        print '\t%r  ->  %r' % (pat, token_id)
        if is_regex:
          #print re_tree
          out_pat = TranslateRegex(pat)
          #print out_pat

      print

  elif action == 'print-regex':
    unique = set()

    num_regexes = 0
    for state, pat_list in lex.LEXER_DEF.iteritems():
      print state
      # This level is re2c patterns.
      for is_regex, pat, token_id in pat_list:
        #print '\t%r  ->  %r' % (pat, token_id)
        if is_regex:
          print '\t' + pat
          print '\t' + TranslateRegex(pat)
          print
          #PrintRegex(pat)
          num_regexes += 1
          unique.add(pat)
        else:
          print '\t' + TranslateConstant(pat)

      print

    print 'Printed %d regexes (%d unique)' % (num_regexes, len(unique))


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
