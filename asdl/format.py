"""
format.py -- Pretty print an ASDL data structure.

Like encode.py, but uses text instead of binary.

TODO:

- auto-abbreviation of single field things (minus location)

- option to omit spaces for SQ, SQ, W?  It's all one thing.

Places where we try a single line:
 - arrays 
 - objects with name fields
 - abbreviated, unnamed fields
"""

import cgi
import io
import json
import re
import sys

from asdl import asdl_ as asdl
from core import util


def DetectConsoleOutput(f):
  """Wrapped to auto-detect."""
  if f.isatty():
    return AnsiOutput(f)
  else:
    return TextOutput(f)


class ColorOutput:
  """Abstract base class for plain text, ANSI color, and HTML color."""

  def __init__(self, f):
    self.f = f
    self.num_chars = 0

  def NewTempBuffer(self):
    """Return a temporary buffer for the line wrapping calculation."""
    raise NotImplementedError

  def FileHeader(self):
    """Hook for printing a full file."""
    pass

  def FileFooter(self):
    """Hook for printing a full file."""
    pass

  def PushColor(self, str_type):
    raise NotImplementedError

  def PopColor(self):
    raise NotImplementedError

  def write(self, s):
    self.f.write(s)
    self.num_chars += len(s)  # Only count visible characters!

  def WriteRaw(self, raw):
    """
    Write raw data without escaping, and without counting control codes in the length.
    """
    s, num_chars = raw
    self.f.write(s)
    self.num_chars += num_chars

  def NumChars(self):
    return self.num_chars

  def GetRaw(self):
    # For when we have an io.StringIO()
    return self.f.getvalue(), self.num_chars


class TextOutput(ColorOutput):
  """TextOutput put obeys the color interface, but outputs nothing."""

  def __init__(self, f):
    ColorOutput.__init__(self, f)

  def NewTempBuffer(self):
    return TextOutput(util.Buffer())

  def PushColor(self, str_type):
    pass  # ignore color

  def PopColor(self):
    pass  # ignore color


class HtmlOutput(ColorOutput):
  """
  HTML one can have wider columns.  Maybe not even fixed-width font.  Hm yeah
  indentation should be logical then?

  Color: HTML spans
  """
  def __init__(self, f):
    ColorOutput.__init__(self, f)

  def NewTempBuffer(self):
    return HtmlOutput(util.Buffer())

  def FileHeader(self):
    # TODO: Use a different CSS file to make the colors match.  I like string
    # literals as yellow, etc.
     #<link rel="stylesheet" type="text/css" href="/css/code.css" />
    self.f.write("""
<html>
  <head>
     <title>oil AST</title>
     <style>
      .n { color: brown }
      .s { font-weight: bold }
      .o { color: darkgreen }
     </style>
  </head>
  <body>
    <pre>
""")

  def FileFooter(self):
    self.f.write("""
    </pre>
  </body>
</html>
    """)

  def PushColor(self, str_type):
    # To save bandwidth, use single character CSS names.
    if str_type == _NODE_TYPE:
      css_class = 'n'
    elif str_type == _STRING_LITERAL:
      css_class = 's'
    elif str_type == _OTHER_LITERAL:
      css_class = 'o'
    elif str_type == _OTHER_TYPE:
      css_class = 'o'
    else:
      raise AssertionError(str_type)
    self.f.write('<span class="%s">' % css_class)

  def PopColor(self):
    self.f.write('</span>')

  def write(self, s):
    # PROBLEM: Double escaping!
    self.f.write(cgi.escape(s))
    self.num_chars += len(s)  # Only count visible characters!


# Color token types
_NODE_TYPE = 1
_STRING_LITERAL = 2
_OTHER_LITERAL = 3  # Int and bool.  Green?
_OTHER_TYPE = 4  # Or


# ANSI color constants (also in sh_spec.py)
_RESET = '\033[0;0m'
_BOLD = '\033[1m'

_RED = '\033[31m'
_GREEN = '\033[32m'
_BLUE = '\033[34m'

_YELLOW = '\033[33m'
_CYAN = '\033[36m'


class AnsiOutput(ColorOutput):
  """For the console."""

  def __init__(self, f):
    ColorOutput.__init__(self, f)

  def NewTempBuffer(self):
    return AnsiOutput(util.Buffer())

  def PushColor(self, str_type):
    if str_type == _NODE_TYPE:
      #self.f.write(_GREEN)
      self.f.write(_YELLOW)
    elif str_type == _STRING_LITERAL:
      self.f.write(_BOLD)
    elif str_type == _OTHER_LITERAL:
      self.f.write(_GREEN)
    elif str_type == _OTHER_TYPE:
      self.f.write(_GREEN)  # Same color as other literals for now
    else:
      raise AssertionError(str_type)

  def PopColor(self):
    self.f.write(_RESET)


#
# Nodes
#


class _Obj:
  """Node for pretty-printing."""
  def __init__(self, node_type):
    self.node_type = node_type
    self.fields = []  # list of 2-tuples of (name, Obj or ColoredString)

    # Custom hooks can change these:
    self.abbrev = False
    self.show_node_type = True  # only respected when abbrev is false
    self.left = '('
    self.right = ')'
    self.unnamed_fields = []  # if this is set, it's printed instead?
                              # problem: CompoundWord just has word_part though
                              # List of Obj or ColoredString

class _ColoredString:
  """Node for pretty-printing."""
  def __init__(self, s, str_type):
    self.s = s
    self.str_type = str_type


def FormatField(obj, field_name, abbrev_hook, omit_empty=True):
  try:
    field_val = getattr(obj, field_name)
  except AttributeError:
    # This happens when required fields are not initialized, e.g. FuncCall()
    # without setting name.
    raise AssertionError(
        '%s is missing field %r' % (obj.__class__, field_name))

  desc = obj.DESCRIPTOR_LOOKUP[field_name]
  if isinstance(desc, asdl.IntType) or isinstance(desc, asdl.BoolType):
    out_val = _ColoredString(str(field_val), _OTHER_LITERAL)

  elif isinstance(desc, asdl.Sum) and asdl.is_simple(desc):
    out_val = field_val.name

  elif isinstance(desc, asdl.StrType):
    out_val = _ColoredString(field_val, _STRING_LITERAL)

  elif isinstance(desc, asdl.ArrayType):
    out_val = []
    obj_list = field_val
    for child_obj in obj_list:
      t = MakeTree(child_obj, abbrev_hook)
      out_val.append(t)

    if omit_empty and not obj_list:
      out_val = None

  elif isinstance(desc, asdl.MaybeType):
    if field_val is None:
      out_val = None
    else:
      out_val = MakeTree(field_val, abbrev_hook)

  else:
    out_val = MakeTree(field_val, abbrev_hook)

  return out_val


def MakeTree(obj, abbrev_hook=None, omit_empty=True):
  """The first step of printing: create a homogeneous tree.

  Args:
    obj: py_meta.Obj
    omit_empty: Whether to omit empty lists
  Returns:
    _Obj node
  """
  from asdl import py_meta

  if isinstance(obj, py_meta.SimpleObj):  # Primitive
    return obj.name

  elif isinstance(obj, py_meta.CompoundObj):
    # These lines can be possibly COMBINED all into one.  () can replace
    # indentation?
    out_node = _Obj(obj.__class__.__name__)
    fields = out_node.fields

    for field_name in obj.FIELDS:
      out_val = FormatField(obj, field_name, abbrev_hook,
                            omit_empty=omit_empty)

      if out_val is not None:
        out_node.fields.append((field_name, out_val))

    # Call user-defined hook to abbreviate compound objects.
    if abbrev_hook:
      abbrev_hook(obj, out_node)

  else:
    # Id uses this now.  TODO: Should we have plugins?  Might need it for
    # color.
    #print('OTHER', obj.__class__, isinstance(obj, py_meta.CompoundObj))
    return _ColoredString(repr(obj), _OTHER_TYPE)

  return out_node


# This is word characters, - and _, as well as path name characters . and /.
_PLAIN_RE = re.compile(r'^[a-zA-Z0-9\-_./]+$')

def _PrettyString(s):
  if '\n' in s:
    return json.dumps(s)  # account for the fact that $ matches the newline
  if _PLAIN_RE.match(s):
    return s
  else:
    return json.dumps(s)


INDENT = 2

def _PrintWrappedArray(array, prefix_len, f, indent, max_col):
  """Print an array of objects with line wrapping.

  Returns whether they all fit on a single line, so you can print the closing
  brace properly.
  """
  all_fit = True
  chars_so_far = prefix_len

  for i, val in enumerate(array):
    if i != 0:
      f.write(' ')

    single_f = f.NewTempBuffer()
    if _TrySingleLine(val, single_f, max_col - chars_so_far):
      f.WriteRaw(single_f.GetRaw())
      chars_so_far += single_f.NumChars()
    else:  # WRAP THE LINE
      f.write('\n')
      # TODO: Add max_col here, taking into account the field name
      new_indent = indent+INDENT
      PrintTree(val, f, indent=new_indent, max_col=max_col)

      chars_so_far = 0  # allow more
      all_fit = False
  return all_fit


def _PrintWholeArray(array, prefix_len, f, indent, max_col):
  # This is UNLIKE the abbreviated case above, where we do WRAPPING.
  # Here, ALL children must fit on a single line, or else we separate
  # each one oonto a separate line.  This is to avoid the following:
  #
  # children: [(C ...)
  #   (C ...)
  # ]
  # The first child is out of line.  The abbreviated objects have a
  # small header like C or DQ so it doesn't matter as much.
  all_fit = True
  pieces = []
  chars_so_far = prefix_len
  for item in array:
    single_f = f.NewTempBuffer()
    if _TrySingleLine(item, single_f, max_col - chars_so_far):
      pieces.append(single_f.GetRaw())
      chars_so_far += single_f.NumChars()
    else:
      all_fit = False
      break

  if all_fit:
    for i, p in enumerate(pieces):
      if i != 0:
        f.write(' ')
      f.WriteRaw(p)
    f.write(']')
  return all_fit


def _PrintTreeObj(node, f, indent, max_col):
  """Print a CompoundObj in abbreviated or normal form."""
  ind = ' ' * indent

  if node.abbrev:  # abbreviated
    prefix = ind + node.left
    f.write(prefix)
    if node.show_node_type:
      f.PushColor(_NODE_TYPE)
      f.write(node.node_type)
      f.PopColor()
      f.write(' ')

    prefix_len = len(prefix) + len(node.node_type) + 1
    all_fit = _PrintWrappedArray(
        node.unnamed_fields, prefix_len, f, indent, max_col)

    if not all_fit:
      f.write('\n')
      f.write(ind)
    f.write(node.right)

  else:  # full form like (SimpleCommand ...)
    f.write(ind + node.left)

    f.PushColor(_NODE_TYPE)
    f.write(node.node_type)
    f.PopColor()

    f.write('\n')
    i = 0
    for name, val in node.fields:
      ind1 = ' ' * (indent+INDENT)
      if isinstance(val, list):  # list field
        name_str = '%s%s: [' % (ind1, name)
        f.write(name_str)
        prefix_len = len(name_str)

        if not _PrintWholeArray(val, prefix_len, f, indent, max_col):
          f.write('\n')
          for child in val:
            # TODO: Add max_col here
            PrintTree(child, f, indent=indent+INDENT+INDENT)
            f.write('\n')
          f.write('%s]' % ind1)

      else:  # primitive field
        name_str = '%s%s: ' % (ind1, name)
        f.write(name_str)
        prefix_len = len(name_str)

        # Try to print it on the same line as the field name; otherwise print
        # it on a separate line.
        single_f = f.NewTempBuffer()
        if _TrySingleLine(val, single_f, max_col - prefix_len):
          f.WriteRaw(single_f.GetRaw())
        else:
          f.write('\n')
          # TODO: Add max_col here, taking into account the field name
          PrintTree(val, f, indent=indent+INDENT+INDENT)
        i += 1

      f.write('\n')  # separate fields

    f.write(ind + node.right)
 

def PrintTree(node, f, indent=0, max_col=100):
  """Second step of printing: turn homogeneous tree into a colored string.

  Args:
    node: homogeneous tree node
    f: ColorOutput instance.
    max_col: don't print past this column number on ANY line
  """
  ind = ' ' * indent

  # Try printing on a single line
  single_f = f.NewTempBuffer()
  single_f.write(ind)
  if _TrySingleLine(node, single_f, max_col - indent):
    f.WriteRaw(single_f.GetRaw())
    return

  if isinstance(node, str):
    f.write(ind + _PrettyString(node))

  elif isinstance(node, _ColoredString):
    f.PushColor(node.str_type)
    f.write(_PrettyString(node.s))
    f.PopColor()

  elif isinstance(node, _Obj):
    _PrintTreeObj(node, f, indent, max_col)

  else:
    raise AssertionError(node)


def _TrySingleLineObj(node, f, max_chars):
  """Print an object on a single line."""
  f.write(node.left)
  if node.abbrev:
    if node.show_node_type:
      f.PushColor(_NODE_TYPE)
      f.write(node.node_type)
      f.PopColor()
      f.write(' ')

    for i, val in enumerate(node.unnamed_fields):
      if i != 0:
        f.write(' ')
      if not _TrySingleLine(val, f, max_chars):
        return False
  else:
    f.PushColor(_NODE_TYPE)
    f.write(node.node_type)
    f.PopColor()

    n = len(node.fields)
    for name, val in node.fields:
      f.write(' %s:' % name)
      if not _TrySingleLine(val, f, max_chars):
        return False

  f.write(node.right)
  return True


def _TrySingleLine(node, f, max_chars):
  """Try printing on a single line.

  Args:
    node: homogeneous tree node
    f: ColorOutput instance
    max_chars: maximum number of characters to print on THIS line
    indent: current indent level

  Returns:
    ok: whether it fit on the line of the given size.
      If False, you can't use the value of f.
  """
  if isinstance(node, str):
    f.write(_PrettyString(node))

  elif isinstance(node, _ColoredString):
    f.PushColor(node.str_type)
    f.write(_PrettyString(node.s))
    f.PopColor()

  elif isinstance(node, list):  # Can we fit the WHOLE list on the line?
    f.write('[')
    for item in node:
      if not _TrySingleLine(item, f, max_chars):
        return False
    f.write(']')

  elif isinstance(node, _Obj):
    return _TrySingleLineObj(node, f, max_chars)

  else:
    raise AssertionError("Unexpected node: %r (%r)" % (node, node.__class__))

  # Take into account the last char.
  num_chars_so_far = f.NumChars()
  if num_chars_so_far > max_chars:
    return False

  return True
