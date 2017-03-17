#!/usr/bin/env python3
"""
glob_.py
"""

try:
  from core import libc
except ImportError:
  from core import fake_libc as libc

# EXAMPLES
#
# Splitting happens before globbing:
#
# pat='*.py *.sh'
# echo $pat  # split into two glob patterns, then expand!

# Parts must be glob-escaped separately:
# echo "core"/*.py
# echo "?core"/*.py

# ---- example:
#
# pat='*.py *.s'
# echo ${pat}h
#
# Array
# -> [PartValue('echo')] [ [PartValue('*.py *.s')  PartValue('h') ]
#    dse=1,dg=0             dse=1, dg=1           dse=0, dg=0
#
# Split, Join and Glob Escape -- but glob escapping depends on globber
# settings!

# -> [ PartValue('echo') ] [ PartValue('*.py') PartValue('*.sh') ]
#      dse=0 dg=0            dse=0 dg=1        dse0=dg1
#
# Maybe it should be
# 
# glob_arg
# [ LiteralArg, GlobArg, LiteralArg ]
#
# ---- example:
#
# argv.py 1${undefined:-"2 3" "4 5"}6
# stdout: ['12 3', '4 56']
#
# So you first evaluate the BracedVarSub, and get
#
# CompoundWord([DoubleQuotedPart("2 3") LiteralPart(" ") DoubleQuotedPart("4 5")
#
# Then you put it into the rest of PartValues
#
# 
# StringPartValue("1", dse=1), 
# StringPartValue("2 3", dse=0)
# StringPartValue(" ", dse=1)  # Because it was unquoted
# StringPartValue("4 5", dse=0)
# StringPartValue("6", dse=0)
#
# StringPartValue turns into ArrayPartValue by SPLITTING.  Duh.
#
# And then you have a bunch of part_values and you just join them.
# Single algorithm to join.

# Tests to make pass:
# - var-sub-quote
# - word-split
# - array: $* and "$*", empty array, etc.

# CLASSES / PIPELINE SKETCH
#
# WordEvaluator(mem, exec_opts)
#   EvalCompoundWord
#   EvalWords
#   EvalEnv
#
# PartEvaluator(mem, exec_opts)
# word_part -> part_value   (go one by one)
#   def Eval(self, part)
#
# Splitter(mem.IFS)
# part_value[] -> part_value[]
#   def Split(self, vals)
#
# Joiner(exec_opts.do_glob)  # for do_glob
# part_value[] -> arg_value[]
#   def JoinAndGlobEscape(vals)
#   Elide()
#
# Globber(exec_opts)
# arg_value[] -> string[]
#   Expand()
#
# Vertical slice:
# - start by evaluating all parts, no splitting, joining, or globbing
# - just the trivial algorithm of joining all the parts.
#   - like IFS='' and noglob?

def LooksLikeGlob():
  """
  TODO: Reference lib/glob /   glob_pattern functions in bash
  grep glob_pattern lib/glob/*

  NOTE: Dash has CTLESC = -127.
  Does that mean a string is an array of ints or shorts?  Not bytes?
  How does it handle unicode/utf-8 then?
  Nope it's using it with char* p.
  So it dash only ASCII or what?  TODO: test it
  
  NOTE: May not need this if we use structured parts.
  """
  pass


# Glob Helpers for WordParts.
# NOTE: Escaping / doesn't work, because it's not a filename character.
# ! : - are metachars within character classes
GLOB_META_CHARS = r'\*?[]-:!'

def GlobEscape(s):
  """
  For SingleQuotedPart, DoubleQuotedPart, and EscapedLiteralPart
  """
  escaped = ''
  for c in s:
    if c in GLOB_META_CHARS:
      escaped += '\\'
    escaped += c
  return escaped


def _GlobUnescape(s):  # used by cmd_exec
  """
  If there is no glob match, just unescape the string.
  """
  unescaped = ''
  i = 0
  n = len(s)
  while i < n:
    c = s[i]
    if c == '\\':
      assert i != n - 1, 'There should be no trailing single backslash!'
      i += 1
      c2 = s[i]
      if c2 in GLOB_META_CHARS:
        unescaped += c2
      else:
        raise AssertionError("Unexpected escaped character %r" % c2)
    else:
      unescaped += c
    i += 1
  return unescaped


class Globber:
  def __init__(self, exec_opts):
    # TODO: separate into set_opts.glob_opts, and sh_opts.glob_opts?  Only if
    # other shels use the same options as bash though.

    self.noglob = False  # set -f

    # shopt: why the difference?  No command line switch I guess.
    self.dotglob = False  # dotfiles are matched
    self.failglob = False  # no matches is an error
    self.globstar = False  # ** for directories
    # globasciiranges - ascii or unicode char classes (unicode by default)
    # nocaseglob
    self.nullglob = False  # no matches evaluates to empty, otherwise
    # extglob: the !() syntax

    # TODO: Figure out which ones are in other shells, and only support those?
    # - Include globstar since I use it, and zsh has it.

  def Expand(self, argv):
    result = []
    for arg in argv:
      # TODO: Only try to glob if there are any glob metacharacters.
      # Or maybe it is a conservative "avoid glob" heuristic?
      #
      # Non-glob but with glob characters:
      # echo ][
      # echo []  # empty
      # echo []LICENSE  # empty
      # echo [L]ICENSE  # this one is good
      # So yeah you need to test the validity somehow.

      try:
        #g = glob.glob(arg)  # Bad Python glob
        # PROBLEM: / is significant and can't be escaped!  Hav eto avoid globbing it.
        g = libc.glob(arg)
      except Exception as e:
        # - [C\-D] is invalid in Python?  Regex compilation error.
        # - [:punct:] not supported
        print("Error expanding glob %r: %s" % (arg, e))
        raise
      #print('G', arg, g)

      if g:
        result.extend(g)
      else:
        u = _GlobUnescape(arg)
        result.append(u)
    return result
