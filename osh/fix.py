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


# NICE mode: Assume that the user isn't relying on word splitting.  A lot of
# users want this!
#
# Problem cases:
# 
# for name in $(find ...); do echo $name; done
#
# This doesn't split.  Heuristic:

NICE = 0

# Try to convert with pedantic correctness.  Not sure if users will want this
# though.  Most people are not super principled about their shell programs.
# But experts might want it.  Experts might want to run ShellCheck first and
# quote everything, and then everything will be unquoted.
PEDANTIC = 1


class Fixer:
  """
  Convert osh code to oil.

  Convert command, word, word_part, arith_expr, bool_expr, etc.
    redirects, ops, etc.

  Other things to convert:
  - builtins
    - set -o errexit to  
    - option +errexit +xtrace +allow-unset
  - brace expansion: haven't done that yet

  - command invocations
    - find invocations
    - xargs

  """

  def __init__(self, cursor, arena, f, mode=NICE):
    self.cursor = cursor
    self.arena = arena
    self.f = f
    # In PEDANTIC mode, we translate unquoted $foo to @-foo, which means it will
    # be split and globbed?
    self.mode = mode

  def End(self):
    end_id = len(self.arena.spans)
    self.cursor.PrintUntil(end_id)

  def DoRedirect(self, node):
    #print(node, file=sys.stderr)
    self.cursor.PrintUntil(node.spids[0])

    # TODO:
    # - Do < and <& the same way.
    # - How to handle here docs and here docs?
    # - >> becomes >+ or >-, or maybe >>>

    if node.fd == -1:
      if node.op_id == Id.Redir_Great:
        self.f.write('>')  # Allow us to replace the operator
        self.cursor.SkipUntil(node.spids[0] + 1)
      elif node.op_id == Id.Redir_GreatAnd:
        self.f.write('> !')  # Replace >& 2 with > !2
        spid = word.LeftMostSpanForWord(node.arg_word)
        self.cursor.SkipUntil(spid)
        #self.DoWord(node.arg_word)

    else:
      # NOTE: Spacing like !2>err.txt vs !2 > err.txt can be done in the
      # formatter.
      self.f.write('!%d ' % node.fd)
      if node.op_id == Id.Redir_Great:
        self.f.write('>')
        self.cursor.SkipUntil(node.spids[0] + 1)
      elif node.op_id == Id.Redir_GreatAnd:
        self.f.write('> !')  # Replace 1>& 2 with !1 > !2
        spid = word.LeftMostSpanForWord(node.arg_word)
        self.cursor.SkipUntil(spid)

    # <<< 'here word'
    # << 'here word'
    #
    # 2> out.txt
    # !2 > out.txt

    # cat 1<< EOF
    # hello $name
    # EOF
    # cat !1 << """
    # hello $name
    # """
    #
    # cat << 'EOF'
    # no expansion
    # EOF
    #   cat <<- 'EOF'
    #   no expansion and indented
    #
    # cat << '''
    # no expansion
    # '''
    #   cat << '''
    #   no expansion and indented
    #   '''

    # Warn about multiple here docs on a line.
    # As an obscure feature, allow
    # cat << _'ONE' << _"TWO"
    # 123
    # ONE
    # 234
    # TWO
    # The _ is an indicator that it's not a string to be piped in.




    pass

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

      # TODO: Need to print until the left most part of the phrase?  the phrase
      # is a word, binding, redirect.
      #self.cursor.PrintUntil()

      if node.more_env:
        # Take advantage and just prefix
        self.f.write('env ')

      for w in node.words:
        self.DoWord(w)

      # NOTE: This will change to "phrase"?  Word or redirect.
      for r in node.redirects:
        self.DoRedirect(r)

      # TODO: Print the terminator.  Could be \n or ;
      # Need to print env like PYTHONPATH = 'foo' && ls
      # Need to print redirects:
      # < > are the same.  << is here string, and >> is assignment.
      # append is >+

    elif node.tag == command_e.Assignment:
      # Print spaces
      # Change RHS to expression language.  Bare words not allowed.  foo ->
      # 'foo'
      #
      # local foo=bar => var foo = 'bar'
      # readonly local foo=bar => foo = 'bar'

      # Do lexical analysis: if it's not a local, then it's a global.
      #
      # local foo=bar
      # foo=new
      # myglobal=2
      #
      # var foo = 'bar'
      # foo := 'new'
      # global myglobal := 2

      # If the RHS is a var sub, then you don't need quotes:
      # local src=${1:-foo}
      #
      # Should be:
      # var src = $1 or 'foo'
      #
      # NOT:
      #
      # var src = $($1 or 'foo')

      for pair in node.pairs:
        if word.IsVarSub(pair.rhs):  # ${1} or "$1"
          # Do it in expression mode
          pass
        # NOTE: ArithSub with $(1 +2 ) is different than 1 + 2 because of
        # conversion to string.
        else:
          # foo=bar -> foo = 'bar'
          pass

    elif node.tag == command_e.Pipeline:  # No changes.
      # Obscure: |& turns into |- or |+ for stderr.
      pass

    elif node.tag == command_e.AndOr:  # No changes
      pass

    elif node.tag == command_e.Fork:
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
      # [[ 1 -eq 2 ]] to (1 == 2)
      self.DoBoolExpr(self.child)

    elif node.tag == command_e.FuncDef:
      # TODO: skip name
      #self.f.write('proc %s' % node.name)

      # Should be the left most span, including 'function'
      self.cursor.PrintUntil(node.spids[0])

      self.f.write('proc ')
      self.f.write(node.name)
      self.cursor.SkipUntil(node.spids[1])

      if node.body.tag == command_e.BraceGroup:
        # Don't add "do" like a standalone brace group.  Just use {}.
        self.DoCommand(node.body)
      else:
        pass
        # Add {}.
        # proc foo {
        #   shell {echo hi; echo bye}
        # }
        #self.DoCommand(node.body)

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

    elif node.tag == command_e.Case:
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
    # Are we getting rid of word joining?  Or maybe keep it but discourage and
    # provide alternatives.
    #
    # You don't really have a problem with byte strings, those are b'foo', but
    # that's in expression mode, not command mode.

    # Problems:
    # - Tilde sub can't be quoted.  ls ~/foo/"foo" are incompatible with the
    # rule.
    # - Globs can't be quoted. ls 'foo'*.py can't be ls "foo*.py" -- it means
    # something different.
    # Might need to finish more of the globber to figure this out.

    # What about here docs words?  It's a double quoted part, but with
    # different formatting!
    if node.tag == word_e.CompoundWord:
      # UNQUOTE simple var subs
      # "$foo" -> $foo
      # "${foo}" -> $foo

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

  def DoWordPart(self, node, quoted=False):
    span_id = word._LeftMostSpanForPart(node)
    if span_id is not None and span_id >= 0:
      span = self.arena.GetLineSpan(span_id)
      #print(span)

      self.cursor.PrintUntil(span_id)

    if node.tag == word_part_e.ArrayLiteralPart:
      pass

    elif node.tag == word_part_e.EscapedLiteralPart:
      # NOTE: If unquoted, it should quoted instead.  ''  \<invisible space>
      pass

    elif node.tag == word_part_e.LiteralPart:
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
        self.DoWordPart(part, quoted=True)

    elif node.tag == word_part_e.SimpleVarSub:
      spid = node.token.span_id
      op_id = node.token.id

      if op_id == Id.VSub_Name:
        self.cursor.PrintUntil(spid + 1)

      elif op_id == Id.VSub_Number:
        self.cursor.PrintUntil(spid + 1)

      elif op_id == Id.VSub_Bang:  # $!
        self.f.write('$Bang')  # TODO
        self.cursor.SkipUntil(spid + 1)

      elif op_id == Id.VSub_At:  # $@
        self.f.write('@Argv')  # PEDANTIC: Depends if quoted or unquoted
        self.cursor.SkipUntil(spid + 1)

      elif op_id == Id.VSub_Pound:  # $#
        self.f.write('$len(Argv)')  # should we have Argc?
        self.cursor.SkipUntil(spid + 1)

      elif op_id == Id.VSub_Pound:  # $$
        self.f.write('$Dollar') 
        self.cursor.SkipUntil(spid + 1)

      elif op_id == Id.VSub_Amp:  # $&
        self.f.write('$Amp') 
        self.cursor.SkipUntil(spid + 1)

      elif op_id == Id.VSub_Star:  # $*
        self.f.write('@Argv')  # PEDANTIC: Depends if quoted or unquoted
        self.cursor.SkipUntil(spid + 1)

      elif op_id == Id.VSub_Hyphen:  # $*
        self.f.write('$Flags')
        self.cursor.SkipUntil(spid + 1)

      elif op_id == Id.VSub_QMark:  # $?
        self.f.write('$Status') 
        self.cursor.SkipUntil(spid + 1)

      else:
        raise AssertionError

    elif node.tag == word_part_e.BracedVarSub:
      left_spid, right_spid = node.spids

      # NOTE: Why do we need this but we don't need it in command sub?
      self.cursor.PrintUntil(left_spid)

      name_spid = node.token.span_id
      op_id = node.token.id

      parens_needed = True
      if node.bracket_op:
        # a[1]
        # These two change the sigil!  ${a[@]} is now @a!
        # a[@] 
        # a[*]
        pass

      if node.prefix_op:
        # len()
        pass
      if node.suffix_op:
        # foo.trimLeft()
        # foo.trimGlobLeft()
        # foo.trimGlobLeft(longest=True)
        #
        # python lstrip() does something different

        # a[1:1]

        # .replace()
        # .replaceGlob()

        pass

      if op_id == Id.VSub_QMark:
        self.cursor.PrintUntil(name_spid + 1)

      if parens_needed:
        # Skip over left bracket and write our own.
        self.f.write('$(')
        self.cursor.SkipUntil(left_spid + 1)

        # Placeholder for now
        self.cursor.PrintUntil(right_spid)

        # Skip over right bracket and write our own.
        self.f.write(')')
      else:
        pass

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

