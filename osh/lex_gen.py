#!/usr/bin/python
"""
lex_gen.py
"""

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


def re2c_convert(re_tree):
  print '\t\t['
  PrintTree(re_tree)
  print '\t\t]'
  return re_tree


  # note: use YYCURSOR and YYLIMIT
  # limit should be the end of string
  # line + line_len
def main(argv):
  # This becomes osh-lex.re2c.c.  It is compiled to osh-lex.c and then
  # included.

  print r"""
/* Common stuff */

/*!re2c
  re2c:define:YYCTYPE = "unsigned char";
  re2c:yyfill:enable = 0;
  re2c:define:YYCURSOR = p;
  re2c:define:YYLIMIT = q;
*/

inline void MatchToken(int lex_mode, unsigned char* line, int line_len,
                       int start_pos, int* id, int* end_pos) {

  unsigned char* p = line + start_pos;  /* modified by re2c */
  unsigned char* q = line + line_len;   /* yylimit */

  // bounds checking
  assert(p < q);
  //printf("p: %p q: %p\n", p, q);

  switch (lex_mode)  {

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

  default:
    assert(0);

  }
}
"""
  return

  # Top level is a switch statement.
  for state, pat_list in lex.LEXER_DEF.iteritems():
    print state
    # This level is re2c patterns.
    for is_regex, pat, token_id in pat_list:
      print '\t%r  ->  %r' % (pat, token_id)
      if is_regex:
        re_tree = sre_parse.parse(pat)
        #print re_tree
        out_pat = re2c_convert(re_tree)
        #print out_pat

    print


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
