#!/usr/bin/python
"""
format.py

Like encode.py, but uses text instead of binary.

For pretty-printing.
"""

import io
import sys

from asdl import asdl_parse as asdl


class ColorOutput:
  """
  API:

  PushColor() ?
  PopColor()?

  Things that should be color: raw text, like "ls" and '/foo/bar"

  certain kinds of nodes.

  Should we have both a background color and a foreground color?
  """
  def __init__(self, f):
    self.f = f
    self.lines = []

  def Write(self, line):
    self.lines.append(line)


class TextOutput(ColorOutput):
  """TextOutput put obeys the color interface, but outputs nothing."""
  def __init__(self, f):
    ColorOutput.__init__(self, f)


class HtmlOutput(ColorOutput):
  """
  HTML one can have wider columns.  Maybe not even fixed-width font.
  Hm yeah indentation should be logical then?

  Color: HTML spans
  """
  def __init__(self, f):
    ColorOutput.__init__(self, f)


class AnsiOutput(ColorOutput):
  """
  Generally 80 column output

  Color: html code and restore

  """

  def __init__(self, f):
    ColorOutput.__init__(self, f)


INDENT = 2

# TODO: Change algorithm
# - MakeTree makes it homogeneous:
#   - strings for primitives, or ? for unset
#   - (field, value) tuple
#   - [] for arrays
#   - _Obj(name, fields)
#
# And then PrintTree(max_col) does 
# temporary buffer
#
# if it fails, then print the tree
# ok = TryPrintLine(child, max_col)
# if (not ok):
#   indent
#   PrintTree()
#
# And PrintTree should take a list of Substitutions on node_type to make it
# shorter?
# - CompoundWord
# - SimpleCommand
# - Lit_Chars for tokens


class _Obj:
  def __init__(self, node_type):
    self.node_type = node_type
    self.fields = []  # list of 2-tuples


def MakeTree(obj, omit_empty=True):
  """
  Args:
    obj: py_meta.Obj
    omit_empty: Whether to omit empty lists
  Returns:
    A tree of strings and lists.

  NOTES:

  {} for words, [] for wordpart?  What about tokens?  I think each node has to
  be able to override the behavior.  How to do this though?  Free functions?

  Common case:
  ls /foo /bar -> (Com {[ls]} {[/foo]} {[/bar]})
  Or use color for this?

  (ArithBinary Plus (ArithBinary Plus (Const 1) (Const 2)) (Const 3))
  vs.
  ArithBinary
    Plus
    ArithBinary
      Plus
      Const 1
      Const 2
    Const 3

  What about field names?

  Inline:
  (Node children:[() () ()])

  Indented
  (Node
    children:[
      () 
      ()
      ()
    ]
  )
  """
  # HACK to incorporate old AST nodes.  Remove when the whole thing is
  # converted.
  from asdl import py_meta
  if not isinstance(obj, py_meta.CompoundObj):
    #raise AssertionError(obj)
    return repr(obj)

  # These lines can be possibly COMBINED all into one.  () can replace
  # indentation?
  out_node = _Obj(obj.__class__.__name__)
  fields = out_node.fields

  for field_name in obj.FIELDS:
    show_field = True
    out_val = ''

    # Need a different data model.  Pairs?
    #print(name)
    try:
      field_val = getattr(obj, field_name)
    except AttributeError:
      out_val = '?'
      continue

    desc = obj.DESCRIPTOR_LOOKUP[field_name]
    if isinstance(desc, asdl.IntType):
      # TODO: How to check for overflow?
      out_val = str(field_val)

    elif isinstance(desc, asdl.Sum) and asdl.is_simple(desc):
      # HACK for now to reflect that Id is an integer.
      if isinstance(field_val, int):
        out_val = str(field_val)
      else:
        out_val = field_val.name

    elif isinstance(desc, asdl.StrType):
      out_val = field_val

    elif isinstance(desc, asdl.ArrayType):
      # Hm does an array need the field name?  I can have multiple arrays like
      # redirects, more_env, and words.  Is there a way to make "words"
      # special?
      out_val = []
      obj_list = field_val
      for child_obj in obj_list:
        t = MakeTree(child_obj)
        out_val.append(t)

      if omit_empty and not obj_list:
        show_field = False

    elif isinstance(desc, asdl.MaybeType):
      if field_val is None:
        show_field = False
      else:
        out_val = MakeTree(field_val)

    else:
      # Recursive call for child records.  Write children before parents.

      # Children can't be written directly to 'out'.  We have to know if they
      # will fit first.
      out_val = MakeTree(field_val)

    if show_field:
      out_node.fields.append((field_name, out_val))

  return out_node


def PrintTree(node, f, indent=0, max_col=100):
  """
    node: homogeneous tree node
    f: output file. TODO: Should take ColorOutput?
  """
  ind = ' ' * indent

  # Try printing on a single line
  single_f = io.StringIO()
  single_f.write(ind)
  if TrySingleLine(node, single_f, max_col=max_col-indent):
    f.write(single_f.getvalue())
    return

  if isinstance(node, str):
    f.write(ind + node)

  elif isinstance(node, _Obj):
    f.write(ind + '(')
    f.write(node.node_type)
    f.write('\n')
    i = 0
    for name, val in node.fields:
      ind1 = ' ' * (indent+INDENT)
      if isinstance(val, list):
        f.write('%s%s: [\n' % (ind1, name))
        for child in val:
          # TODO: Add max_col here
          PrintTree(child, f, indent=indent+INDENT+INDENT)
          f.write('\n')
        f.write('%s]' % ind1)
      else:
        f.write('%s%s:\n' % (ind1, name))
        # TODO: Add max_col here, taking into account the field name
        PrintTree(val, f, indent=indent+INDENT+INDENT)
        i += 1
      f.write('\n')  # separate fields

    f.write(ind + ')')

  else:
    raise AssertionError(node)


def TrySingleLine(node, f, max_col=80):
  """Try printing on a single line.

  Args:
    node: homogeneous tree node
    f: output file. TODO: Should take ColorOutput?
    max_col: maximum length of the line
    indent: current indent level

  Returns:
    ok: whether it fit on the line of the given size.
      If False, you can't use the value of f.
  """
  if isinstance(node, str):
    f.write(node)

  elif isinstance(node, _Obj):
    f.write('(')
    f.write(node.node_type)
    n = len(node.fields)
    i = 0
    for name, val in node.fields:
      f.write(' %s:' % name)
      if not TrySingleLine(val, f):
        return False

      i += 1

    f.write(')')

  elif isinstance(node, list):
    f.write('[')
    for item in node:
      if not TrySingleLine(item, f):
        return False
    f.write(']')
  else:
    raise AssertionError(p)

  # Take into account the last char.
  num_chars_so_far = len(f.getvalue()) 
  if num_chars_so_far > max_col:
    return False

  return True
