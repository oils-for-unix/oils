#!/usr/bin/python
"""
pool.py - Sketch of memory management, like you would do in C++.
"""

import sys


### How to get a token value for execution
#
# It has a pointer to the middle of a std::string?  And a length?
# Reader owns the std::string buffers?
# Need to eliminate COMMENTS from memory so we don't have an execution penalty
# for using comments.

### How to get a snippet for an error traceback from a token
#  We need to display the file name and line_num
#
# self.AddErrorContext(token, "Message", args)
# - TODO: maybe add a word too
#
# 1. Take the token.
# 2. Look up line number in the Reader
#
# Reader() -- does it make sense to have one per file, or have a unified one?
# The reader can be
# - InteractiveLineReader
# - StringLineReader
#
# Maybe you need two classes:
#
# LinePool  -- per interpreter
# - the thing that owns the list of std::string
# - it will have a list of filenames too
# DebugInfo -- per interpreter
#
# And then Reader/Lexer/etc. are PER FILE
#
# class Token:
#   pool_index   # index into LinePool
#   col          # begin col
#   length       # end
# And then that contains the (filename, actual line number)
#
# class LinePool
#   Line lines[]
#   std::vector filenames;  // filenames in order that we read them.
#                           // NOTE: we need to normalize them.  Can we use
#                           // the inode num?.
#                           // do mksh/dash just parse the whole thing again?
#                           // there is no cache?
#   Clear()  -- If the parser detects a function, we have to move it?

# struct Line
#   std::string buf;
#   int file_num;  // index into filenames
#   int line_num;  // physical line number

## tuple: std::string, line_num
#
# ANOTHER OPTION: Just COPY the subset of the strings that you need.  Don't
# try to share.
# - This gets rid of a line of leading spaces and trailing comments
# - Might simplify code too
#
# Have a StringPool

# NAH -- This is over optimizing for size.

# HM: At first thought, you can do hashing of first words/ hashing of var
# names / copying and NUL termination of tokens (for execvpe() ) as parse
# time.
#
# But for some shell scripts this could be inefficient?  Hashes could come in
# a second memoizing step.  When a var is looked up, its hash value is cached
# forever.  (does this interfere with fork/COW)?

# In C++, InteractiveLineReader and StringLineReader should use the same
# representation: std::string with internal NULs to terminate lines, and then
# std::vector<char*> that points into to it.
# InteractiveLineReader only needs to save a line if it contains a function.
# The parser needs to set a flag if it contains a function!


class Pool(object):
  """Owns source lines plus debug info.

  The Lexer will use the Reader and LineLexer to produce tokens.

  The LinePool has to be passed into both the parser and executor?
  And also parts need to be able to print themselves.. hm.
  """
  def __init__(self):
    # Could be std::vector<char *> pointing into a std::string
    self.lines = []
    self.debug_info = []  # list of (src_path index, line index)
    self.src_paths = []  # list of source paths
    self.src_index = -1  # index of current source file
    self.mark_index = 0

    # Pools of objects.  Tokens are fixed size value objects?  Or I suppose
    # they could be allocated here.  If they are 16 bytes instead of 8 bytes
    # maybe that's a win on 32 bit?
    self.parts = []  # WordPart
    self.words = []  # Word
    self.nodes = []

  # NOTE: dash uses this same scheme.  stalloc() / setstackmark() /
  # popstackmark() in memalloc.c.

  def Mark(self):
    """In interactive mode, call this before reading lines."""
    self.mark_index = len(self.lines)
    # TODO: Mark parts, words, nodes too

  def Erase(self):
    """
    Erase last lines from the pool.  This is done if there were no function
    definitions, after we executed everything.
    """
    # Delete the last ones
    del self.lines[self.mark_index : ]
    # TODO: Delete parts, words, nodes too

  def AddSourcePath(self, src_path):
    self.src_paths.append(src_path)
    self.src_index += 1

  def AddLine(self, line, line_num):
    pool_index = len(self.lines)
    self.lines.append(line)
    self.debug_info.append((self.src_index, line_num))
    return pool_index

  def GetLine(self, pool_index):
    """
    Given an line ID, return the actual filename, physical line number, and
    line contents.
    """
    return self.lines[pool_index]

  def GetDebugInfo(self, pool_index):
    src_index, line_num = self.debug_info[pool_index]
    try:
      path = self.src_paths[src_index]
    except IndexError:
      print('INDEX', src_index)
      raise
    return path, line_num

  def NewLiteralPart(self):
    pass

  # PROBLEM: I don't want a wrapper for every single type?  That is annoying.
  # Should I have homogeneous nodes like C?
  # Or I could generate this code from constructors?

  # Parts: 6 or so types
  # Word: 2 types
  # VarOp: 5 or so types
  # CNode: 10 or so types
  #   Redirects: 3 types
  # BNode: 4 or so types
  # ExprNode: 4 or so types

  # Another thing we could do is just generate a method for every type?

  def OwnPart(self, part):
    pass

  def OwnWord(self, word):
    pass
  # So all the nodes inherit from a common base class.  It has a virtual
  # destructor.  It can just be Object* or Node*.  A Word and a Part is a Node
  # too.

  # foo = Bar()
  # pool.Own(foo)

  # Alternative: Use placement new.  That's what the Dart parser uses.
  # Does that allow multiple interpreters in the same binary in different
  # threads?  I'm not sure I even need that though.
