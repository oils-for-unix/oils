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
from typing import Tuple, List

from _devbuild.gen.hnode_asdl import (
    hnode_e, hnode_t, hnode__Record, hnode__Array, hnode__Leaf,
    hnode__External, color_e, color_t, color_str, hnode_str,
)
from asdl import pretty
from pylib import cgi
from mycpp import mylib

from typing import cast


def DetectConsoleOutput(f):
  # type: (mylib.Writer) -> ColorOutput
  """Wrapped to auto-detect."""
  if f.isatty():
    return AnsiOutput(f)
  else:
    return TextOutput(f)


class ColorOutput(object):
  """Abstract base class for plain text, ANSI color, and HTML color."""

  def __init__(self, f):
    # type: (mylib.Writer) -> None
    self.f = f
    self.num_chars = 0

  def NewTempBuffer(self):
    # type: () -> ColorOutput
    """Return a temporary buffer for the line wrapping calculation."""
    raise NotImplementedError()

  def FileHeader(self):
    # type: () -> None
    """Hook for printing a full file."""
    pass

  def FileFooter(self):
    # type: () -> None
    """Hook for printing a full file."""
    pass

  def PushColor(self, e_color):
    # type: (color_t) -> None
    raise NotImplementedError()

  def PopColor(self):
    # type: () -> None
    raise NotImplementedError()

  def write(self, s):
    # type: (str) -> None
    self.f.write(s)
    self.num_chars += len(s)  # Only count visible characters!

  def WriteRaw(self, raw):
    # type: (Tuple[str, int]) -> None
    """
    Write raw data without escaping, and without counting control codes in the
    length.
    """
    s, num_chars = raw
    self.f.write(s)
    self.num_chars += num_chars

  def NumChars(self):
    # type: () -> int
    return self.num_chars

  def GetRaw(self):
    # type: () -> Tuple[str, int]

    # NOTE: Ensured by NewTempBuffer()
    f = cast(mylib.BufWriter, self.f)
    return f.getvalue(), self.num_chars


class TextOutput(ColorOutput):
  """TextOutput put obeys the color interface, but outputs nothing."""

  def __init__(self, f):
    # type: (mylib.Writer) -> None
    ColorOutput.__init__(self, f)

  def NewTempBuffer(self):
    # type: () -> TextOutput
    return TextOutput(mylib.BufWriter())

  def PushColor(self, e_color):
    # type: (color_t) -> None
    pass  # ignore color

  def PopColor(self):
    # type: () -> None
    pass  # ignore color


class HtmlOutput(ColorOutput):
  """
  HTML one can have wider columns.  Maybe not even fixed-width font.  Hm yeah
  indentation should be logical then?

  Color: HTML spans
  """
  def __init__(self, f):
    # type: (mylib.Writer) -> None
    ColorOutput.__init__(self, f)

  def NewTempBuffer(self):
    # type: () -> HtmlOutput
    return HtmlOutput(mylib.BufWriter())

  def FileHeader(self):
    # type: () -> None
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
    # type: () -> None
    self.f.write("""
    </pre>
  </body>
</html>
    """)

  def PushColor(self, e_color):
    # type: (color_t) -> None
    # To save bandwidth, use single character CSS names.
    if e_color == color_e.TypeName:
      css_class = 'n'
    elif e_color == color_e.StringConst:
      css_class = 's'
    elif e_color == color_e.OtherConst:
      css_class = 'o'
    elif e_color == color_e.External:
      css_class = 'o'
    elif e_color == color_e.UserType:
      css_class = 'o'
    else:
      raise AssertionError(color_str(e_color))
    self.f.write('<span class="%s">' % css_class)

  def PopColor(self):
    # type: () -> None
    self.f.write('</span>')

  def write(self, s):
    # type: (str) -> None

    # PROBLEM: Double escaping!
    self.f.write(cgi.escape(s))
    self.num_chars += len(s)  # Only count visible characters!


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
    # type: (mylib.Writer) -> None
    ColorOutput.__init__(self, f)

  def NewTempBuffer(self):
    # type: () -> AnsiOutput
    return AnsiOutput(mylib.BufWriter())

  def PushColor(self, e_color):
    # type: (color_t) -> None
    if e_color == color_e.TypeName:
      self.f.write(_YELLOW)
    elif e_color == color_e.StringConst:
      self.f.write(_BOLD)
    elif e_color == color_e.OtherConst:
      self.f.write(_GREEN)
    elif e_color == color_e.External:
      self.f.write(_BOLD + _BLUE)
    elif e_color == color_e.UserType:
      self.f.write(_GREEN)  # Same color as other literals for now
    else:
      raise AssertionError(color_str(e_color))

  def PopColor(self):
    # type: () -> None
    self.f.write(_RESET)


INDENT = 2

class _PrettyPrinter(object):
  def __init__(self, max_col):
    # type: (int) -> None
    self.max_col = max_col

  def _PrintWrappedArray(self, array, prefix_len, f, indent):
    # type: (List[hnode_t], int, ColorOutput, int) -> bool
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
      if _TrySingleLine(val, single_f, self.max_col - chars_so_far):
        s, num_chars = single_f.GetRaw()  # extra unpacking for mycpp
        f.WriteRaw((s, num_chars))
        chars_so_far += single_f.NumChars()
      else:  # WRAP THE LINE
        f.write('\n')
        self.PrintNode(val, f, indent + INDENT)

        chars_so_far = 0  # allow more
        all_fit = False
    return all_fit

  def _PrintWholeArray(self, array, prefix_len, f, indent):
    # type: (List[hnode_t], int, ColorOutput, int) -> bool

    # This is UNLIKE the abbreviated case above, where we do WRAPPING.
    # Here, ALL children must fit on a single line, or else we separate
    # each one onto a separate line.  This is to avoid the following:
    #
    # children: [(C ...)
    #   (C ...)
    # ]
    # The first child is out of line.  The abbreviated objects have a
    # small header like C or DQ so it doesn't matter as much.
    all_fit = True
    pieces = []  # type: List[Tuple[str, int]]
    chars_so_far = prefix_len
    for item in array:
      single_f = f.NewTempBuffer()
      if _TrySingleLine(item, single_f, self.max_col - chars_so_far):
        s, num_chars = single_f.GetRaw()  # extra unpacking for mycpp
        pieces.append((s, num_chars))
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

  def _PrintRecord(self, node, f, indent):
    # type: (hnode__Record, ColorOutput, int) -> None
    """Print a CompoundObj in abbreviated or normal form."""
    ind = ' ' * indent

    if node.abbrev:  # abbreviated
      prefix = ind + node.left
      f.write(prefix)
      if len(node.node_type):
        f.PushColor(color_e.TypeName)
        f.write(node.node_type)
        f.PopColor()
        f.write(' ')

      prefix_len = len(prefix) + len(node.node_type) + 1
      all_fit = self._PrintWrappedArray(
          node.unnamed_fields, prefix_len, f, indent)

      if not all_fit:
        f.write('\n')
        f.write(ind)
      f.write(node.right)

    else:  # full form like (SimpleCommand ...)
      f.write(ind + node.left)

      f.PushColor(color_e.TypeName)
      f.write(node.node_type)
      f.PopColor()

      f.write('\n')
      i = 0
      for field in node.fields:
        name = field.name
        val = field.val

        ind1 = ' ' * (indent+INDENT)
        UP_val = val  # for mycpp
        tag = val.tag_()
        if tag == hnode_e.Array:
          val = cast(hnode__Array, UP_val)

          name_str = '%s%s: [' % (ind1, name)
          f.write(name_str)
          prefix_len = len(name_str)

          if not self._PrintWholeArray(val.children, prefix_len, f, indent):
            f.write('\n')
            for child in val.children:
              self.PrintNode(child, f, indent+INDENT+INDENT)
              f.write('\n')
            f.write('%s]' % ind1)

        else:  # primitive field
          name_str = '%s%s: ' % (ind1, name)
          f.write(name_str)
          prefix_len = len(name_str)

          # Try to print it on the same line as the field name; otherwise print
          # it on a separate line.
          single_f = f.NewTempBuffer()
          if _TrySingleLine(val, single_f, self.max_col - prefix_len):
            s, num_chars = single_f.GetRaw()  # extra unpacking for mycpp
            f.WriteRaw((s, num_chars))
          else:
            f.write('\n')
            self.PrintNode(val, f, indent+INDENT+INDENT)
          i += 1

        f.write('\n')  # separate fields

      f.write(ind + node.right)

  def PrintNode(self, node, f, indent):
    # type: (hnode_t, ColorOutput, int) -> None
    """Second step of printing: turn homogeneous tree into a colored string.

    Args:
      node: homogeneous tree node
      f: ColorOutput instance.
      max_col: don't print past this column number on ANY line
        NOTE: See asdl/run.sh line-length-hist for a test of this.  It's
        approximate.
        TODO: Use the terminal width.
    """
    ind = ' ' * indent

    # Try printing on a single line
    single_f = f.NewTempBuffer()
    single_f.write(ind)
    if _TrySingleLine(node, single_f, self.max_col - indent):
      s, num_chars = single_f.GetRaw()  # extra unpacking for mycpp
      f.WriteRaw((s, num_chars))
      return

    UP_node = node  # for mycpp
    tag = node.tag_()
    if tag == hnode_e.Leaf:
      node = cast(hnode__Leaf, UP_node)
      f.PushColor(node.color)
      f.write(pretty.String(node.s))
      f.PopColor()

    elif tag == hnode_e.External:
      node = cast(hnode__External, UP_node)
      f.PushColor(color_e.External)
      f.write(repr(node.obj))
      f.PopColor()

    elif tag == hnode_e.Record:
      node = cast(hnode__Record, UP_node)
      self._PrintRecord(node, f, indent)

    else:
      raise AssertionError(hnode_str(tag))


def _TrySingleLineObj(node, f, max_chars):
  # type: (hnode__Record, ColorOutput, int) -> bool
  """Print an object on a single line."""
  f.write(node.left)
  if node.abbrev:
    if len(node.node_type):
      f.PushColor(color_e.TypeName)
      f.write(node.node_type)
      f.PopColor()
      f.write(' ')

    for i, val in enumerate(node.unnamed_fields):
      if i != 0:
        f.write(' ')
      if not _TrySingleLine(val, f, max_chars):
        return False
  else:
    f.PushColor(color_e.TypeName)
    f.write(node.node_type)
    f.PopColor()

    for field in node.fields:
      f.write(' %s:' % field.name)
      if not _TrySingleLine(field.val, f, max_chars):
        return False

  f.write(node.right)
  return True


def _TrySingleLine(node, f, max_chars):
  # type: (hnode_t, ColorOutput, int) -> bool
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
  UP_node = node  # for mycpp
  tag = node.tag_()
  if tag == hnode_e.Leaf:
    node = cast(hnode__Leaf, UP_node)
    f.PushColor(node.color)
    f.write(pretty.String(node.s))
    f.PopColor()

  elif tag == hnode_e.External:
    node = cast(hnode__External, UP_node)

    f.PushColor(color_e.External)
    f.write(repr(node.obj))
    f.PopColor()

  elif tag == hnode_e.Array:
    node = cast(hnode__Array, UP_node)

    # Can we fit the WHOLE array on the line?
    f.write('[')
    for i, item in enumerate(node.children):
      if i != 0:
        f.write(' ')
      if not _TrySingleLine(item, f, max_chars):
        return False
    f.write(']')

  elif tag == hnode_e.Record:
    node = cast(hnode__Record, UP_node)

    return _TrySingleLineObj(node, f, max_chars)

  else:
    raise AssertionError(hnode_str(tag))

  # Take into account the last char.
  num_chars_so_far = f.NumChars()
  if num_chars_so_far > max_chars:
    return False

  return True


def PrintTree(node, f):
  # type: (hnode_t, ColorOutput) -> None
  pp = _PrettyPrinter(100)  # max_col
  pp.PrintNode(node, f, 0)  # indent
