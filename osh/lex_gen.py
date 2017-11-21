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

  print """

inline void MatchToken(int lex_mode, char* line, int line_len, int start_index,
                int* id, int* end_index) {
  switch (lex_mode)  {
  case lex_mode__OUTER:
    *id = id__Lit_Chars;
    //*id = id__Lit_Other;
    *end_index = 3;
    break;
  case lex_mode__COMMENT:
    *id = id__Lit_Other;
    *end_index = 5;
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
