#!/usr/bin/python
"""
fix.py -- Do source transformations.  Somewhat like 'go fix'.
"""

import sys

from core import word
from core.id_kind import Id

from osh import ast_ as ast

command_e = ast.command_e
word_e = ast.word_e
word_part_e = ast.word_part_e
arith_expr_e = ast.arith_expr_e
bool_expr_e = ast.bool_expr_e


class Cursor:
  """
  Wrapper for printing/transforming a complete source file stored in a single
  arena.
  """

  def __init__(self, arena, f):
    self.arena = arena
    self.f = f
    self.next_span_id = 0

  def PrintUntil(self, until_span_id):
    for span_id in range(self.next_span_id, until_span_id):
      span = self.arena.GetLineSpan(span_id)
      line = self.arena.GetLine(span.line_id)
      piece = line[span.col : span.col + span.length]
      self.f.write(piece)
      # Spacing
      #self.f.write('%r' % piece)
    #self.f.write('__')

    self.next_span_id = until_span_id

  def SkipUntil(self, next_span_id):
    """Skip everything before next_span_id.
    Printing will start at next_span_id
    """
    self.next_span_id = next_span_id


# Should this just take an arena, which has all three things?

def Print(arena, node):
  #print node
  #print(spans)

  # TODO: 
  # - Attach span_id to every node, with  "attributes" I guess
  #   - or do it manually on arithmetic first

  # - Then do 

  # First pass:
  # - f() {} to proc f {}
  # - $(( )) and $[ ]  to $()
  # - ${foo} to $(foo)
  # - $(echo hi) to $[echo hi]
  #
  # Dispatch on node.type I guess.
  #
  # or just try 'echo $( echo hi )'  -- preserving whitespace

  # def Fix(node, cursor, f):
  #  cursor.PrintUntil(node._begin_id, f)
  #  print(Reformat(node))
  #  cursor.Skip(node._end_id)

  #  for child in node.children:
  #    Fix(node, cursor, f)
  #
  # "node" is a node tof ix

  if 0:
    for i, span in enumerate(arena.spans):
      line = arena.GetLine(span.line_id)
      piece = line[span.col : span.col + span.length]
      print('%5d %r' % (i, piece))
    print('(%d spans)' % len(arena.spans))

  cursor = Cursor(arena, sys.stdout)
  fixer = Fixer(cursor, arena, sys.stdout)
  fixer.DoCommand(node)
  fixer.End()

  #print('')


class Fixer:

  def __init__(self, cursor, arena, f):
    self.cursor = cursor
    self.arena = arena
    self.f = f

  def End(self):
    end_id = len(self.arena.spans)
    self.cursor.PrintUntil(end_id)

  def DoCommand(self, node):
    if node.tag == command_e.CommandList:
      # TODO: How to distinguish between echo hi; echo bye; and on separate
      # lines
      for child in node.children:
        self.DoCommand(child)

    elif node.tag == command_e.SimpleCommand:
      # How to preserve spaces between words?  Do you want to do it?
      # Well you need to test this:
      #
      # echo foo \
      #   bar

      for w in node.words:
        self.DoWord(w)
      # TODO: Print the terminator.  Could be \n or ;
      # Need to print env like PYTHONPATH = 'foo' && ls
      # Need to print redirects:
      # < > are the same.  << is here string, and >> is assignment.
      # append is >+

    elif node.tag == command_e.Assignment:
      # print spaces
      # change RHS to expression language.  Literal not allowed.  foo -> 'foo'
      # var foo = 'bar'
      # foo := 'bar'
      # foo ::= 'bar'
      # deprecated assignment:  create a local or mutate a global

      # local foo=bar => var foo = 'bar'
      # readonly foo=bar => foo = 'bar'

      # RHS is either a string or an array
      pass

    elif node.tag == command_e.Pipeline:  # No changes.
      pass

    elif node.tag == command_e.AndOr:  # No changes
      pass

    elif node.tag == command_e.Fork:
      # Then do the command?
      # 'ls &' to 'fork ls'
      self.f.write('fork ')

    # This has to be different in the function case.
    #elif node.tag == command_e.BraceGroup:
      # { echo hi; } -> do { echo hi }
      # For now it might be OK to keep 'do { echo hi; }
    #  self.f.write('do')

    elif node.tag == command_e.Subshell:
      # (echo hi) -> shell echo hi
      # (echo hi; echo bye) -> shell {echo hi; echo bye}
      self.f.write('shell ')

    elif node.tag == command_e.DParen:
      # Just change (( )) to ( )
      # Test it with while loop
      self.DoArithExpr(self.child)

    elif node.tag == command_e.DBracket:
      self.DoBoolExpr(self.child)

    elif node.tag == command_e.FuncDef:
      # TODO: skip name
      #self.f.write('proc %s' % node.name)

      # Should be the left most span, including 'function'
      self.cursor.PrintUntil(node.spids[0])

      self.f.write('proc ')
      self.f.write(node.name)
      self.cursor.SkipUntil(node.spids[1])

      self.DoCommand(node.body)

    elif node.tag == command_e.BraceGroup:
      for child in node.children:
        self.DoCommand(child)

    elif node.tag == command_e.ForEach:
      # Need to preserve spaces between words, because there can be line
      # wrapping.
      # for x in a b c \
      #    d e f; do

      self.cursor.PrintUntil(node.spids[0] + 1)  # 'for x in' and then space
      self.f.write('[')
      for i, w in enumerate(node.iter_words):
        if i != 0:
          #self.f.write('_')
          pass
        self.DoWord(w)
      self.f.write(']')

      # TODO: Skip over ; if it's present.  How?
      self._FixDoGroup(node.body)

    elif node.tag == command_e.ForExpr:
      # Change (( )) to ( ), and then _FixDoGroup
      pass

    elif node.tag == command_e.While:
      # I think like this?
      # omit semicolon, but don't omit newline!
      # self.DoCommand(node.cond, omit_semi_if_simple)

      # TODO: Skip over ; if it's present.  How?
      self._FixDoGroup(node.body)

    elif node.tag == command_e.If:
      # Change then/elif/fi to braces
      pass

    else:
      print('Command not handled', node)
      raise AssertionError(node.tag)

  def _FixDoGroup(self, body_node):
    # TODO: Can factor into DoDoGroup()
    do_spid, done_spid = body_node.spids
    self.cursor.PrintUntil(do_spid)
    self.cursor.SkipUntil(do_spid + 1)
    self.f.write('{')

    self.DoCommand(body_node)

    self.cursor.PrintUntil(done_spid)
    self.cursor.SkipUntil(done_spid + 1)
    self.f.write('}')

    #self.DoCommand(node.body)

  def DoWord(self, node):
    # What about here docs words?  It's a double quoted part, but with
    # different formatting!
    if node.tag == word_e.CompoundWord:
      # TODO: I think we have to print the beginning and the end?

      left_spid = word.LeftMostSpanForWord(node)
      #right_spid = word.RightMostSpanForWord(node)
      right_spid = -1
      #print('DoWord %s %s' % (left_spid, right_spid), file=sys.stderr)

      if left_spid >= 0:
        #span = self.arena.GetLineSpan(span_id)
        #print(span)

        #self.cursor.PrintUntil(left_spid)
        pass

      # TODO: 'foo'"bar" should be "foobar", etc.
      # If any part is double quoted, you can always double quote the whole
      # thing?
      for part in node.parts:
        self.DoWordPart(part)

      if right_spid >= 0:
        #self.cursor.PrintUntil(right_spid)
        pass

    else:
      raise AssertionError(node.tag)

  def DoWordPart(self, node):
    span_id = word._LeftMostSpanForPart(node)
    if span_id is not None and span_id >= 0:
      span = self.arena.GetLineSpan(span_id)
      #print(span)

      self.cursor.PrintUntil(span_id)

    if node.tag == word_part_e.LiteralPart:
      # Print it literally.
      # TODO: We might want to do it all on the word level though.  For
      # example, foo"bar" becomes "foobar" in oil.
      spid = node.token.span_id
      self.cursor.PrintUntil(spid + 1)

    elif node.tag == word_part_e.TildeSubPart:  # No change
      pass

    elif node.tag == word_part_e.SingleQuotedPart:
      # TODO: 
      # '\n' is '\\n'
      # $'\n' is '\n'
      pass

    elif node.tag == word_part_e.DoubleQuotedPart:
      for part in node.parts:
        self.DoWordPart(part)

    elif node.tag == word_part_e.SimpleVarSub:
      spid = node.token.span_id
      self.cursor.PrintUntil(spid + 1)

    elif node.tag == word_part_e.BracedVarSub:
      left_spid, right_spid = node.spids

      # NOTE: Why do we need this but we don't need it in command sub?
      self.cursor.PrintUntil(left_spid)

      # Skip over left bracket and write our own.
      self.f.write('$(')
      self.cursor.SkipUntil(left_spid + 1)

      # TODO: Do ops.
      if node.bracket_op:
        pass
      if node.prefix_op:
        pass
      if node.suffix_op:
        pass

      # Placeholder for now
      self.cursor.PrintUntil(right_spid)

      # Skip over right bracket and write our own.
      self.f.write(')')
      self.cursor.SkipUntil(right_spid + 1)

    elif node.tag == word_part_e.CommandSubPart:
      left_spid, right_spid = node.spids

      #self.cursor.PrintUntil(left_spid)
      self.f.write('$[')
      self.cursor.SkipUntil(left_spid + 1)

      self.DoCommand(node.command_list)

      self.f.write(']')
      self.cursor.SkipUntil(right_spid + 1)
      # change to $[echo hi]

    elif node.tag == word_part_e.ArithSubPart:
      left_spid, right_spid = node.spids

      # Skip over left bracket and write our own.
      self.f.write('$(')
      self.cursor.SkipUntil(left_spid + 1)

      # NOTE: This doesn't do anything yet.
      self.DoArithExpr(node.anode)
      # Placeholder for now
      self.cursor.PrintUntil(right_spid - 1)

      # Skip over right bracket and write our own.
      self.f.write(')')
      self.cursor.SkipUntil(right_spid + 1)

    else:
      print('WordPart not handled', node)
      raise AssertionError(node.tag)

  def DoArithExpr(self, node):
    if node.tag == arith_expr_e.ArithBinary:
      # Maybe I should just write the left span and right span for each word?
      #self.f.write(str(node.left))

      if node.op_id == Id.Arith_Plus:
        # NOTE: Right isn't necessarily a word!
        r_id = word.LeftMostSpanForWord(node.right.w)
        #self.cursor.SkipUntil(r_id)
        #self.f.write('PLUS')

      #self.f.write(str(node.right))
    else:
      raise AssertionError(node.tag)

  def DoBoolExpr(self, node):
    # TODO: switch on node.tag
    pass

# WordPart?

# array_item
#
# These get turned into expressions
#
# bracket_op
# suffix_op
# prefix_op

