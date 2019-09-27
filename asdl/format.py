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
from typing import Tuple, List, IO

from cStringIO import StringIO

from asdl import pretty
from asdl import runtime
from pylib import cgi


def DetectConsoleOutput(f):
  # type: (IO[str]) -> ColorOutput
  """Wrapped to auto-detect."""
  if f.isatty():
    return AnsiOutput(f)
  else:
    return TextOutput(f)


class ColorOutput(object):
  """Abstract base class for plain text, ANSI color, and HTML color."""

  def __init__(self, f):
    # type: (IO[str]) -> None
    self.f = f
    self.num_chars = 0

  def NewTempBuffer(self):
    # type: () -> ColorOutput
    """Return a temporary buffer for the line wrapping calculation."""
    raise NotImplementedError

  def FileHeader(self):
    # type: () -> None
    """Hook for printing a full file."""
    pass

  def FileFooter(self):
    # type: () -> None
    """Hook for printing a full file."""
    pass

  def PushColor(self, e_color):
    # type: (int) -> None
    raise NotImplementedError

  def PopColor(self):
    # type: () -> None
    raise NotImplementedError

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
    # NOTE: When wrapping, self.f will be a StringIO with this method.
    return self.f.getvalue(), self.num_chars  # type: ignore


class TextOutput(ColorOutput):
  """TextOutput put obeys the color interface, but outputs nothing."""

  def __init__(self, f):
    # type: (IO[str]) -> None
    ColorOutput.__init__(self, f)

  def NewTempBuffer(self):
    # type: () -> TextOutput
    return TextOutput(StringIO())

  def PushColor(self, e_color):
    # type: (int) -> None
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
    # type: (IO[str]) -> None
    ColorOutput.__init__(self, f)

  def NewTempBuffer(self):
    # type: () -> HtmlOutput
    return HtmlOutput(StringIO())

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
    # type: (int) -> None
    # To save bandwidth, use single character CSS names.
    if e_color == runtime.Color_TypeName:
      css_class = 'n'
    elif e_color == runtime.Color_StringConst:
      css_class = 's'
    elif e_color == runtime.Color_OtherConst:
      css_class = 'o'
    elif e_color == runtime.Color_PythonType:
      css_class = 'o'
    elif e_color == runtime.Color_UserType:
      css_class = 'o'
    else:
      raise AssertionError(e_color)
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
    # type: (IO[str]) -> None
    ColorOutput.__init__(self, f)

  def NewTempBuffer(self):
    # type: () -> AnsiOutput
    return AnsiOutput(StringIO())

  def PushColor(self, e_color):
    # type: (int) -> None
    if e_color == runtime.Color_TypeName:
      self.f.write(_YELLOW)
    elif e_color == runtime.Color_StringConst:
      self.f.write(_BOLD)
    elif e_color == runtime.Color_OtherConst:
      self.f.write(_GREEN)
    elif e_color == runtime.Color_PythonType:
      self.f.write(_BOLD + _BLUE)
    elif e_color == runtime.Color_UserType:
      self.f.write(_GREEN)  # Same color as other literals for now
    else:
      raise AssertionError(e_color)

  def PopColor(self):
    # type: () -> None
    self.f.write(_RESET)


INDENT = 2

def _PrintWrappedArray(array,  # type: List[runtime._PrettyBase]
                       prefix_len,  # type: int
                       f,  # type: ColorOutput
                       indent,  # type: int
                       max_col,  # type: int
                       ):
  # type: (...) -> bool
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
      new_indent = indent + INDENT
      PrintTree(val, f, indent=new_indent, max_col=max_col)

      chars_so_far = 0  # allow more
      all_fit = False
  return all_fit


def _PrintWholeArray(array, prefix_len, f, indent, max_col):
  # type: (List[runtime._PrettyBase], int, ColorOutput, int, int) -> bool

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
  pieces = []  # type: List[Tuple[str, int]]
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
  # type: (runtime.PrettyNode, ColorOutput, int, int) -> None
  """Print a CompoundObj in abbreviated or normal form."""
  ind = ' ' * indent

  if node.abbrev:  # abbreviated
    prefix = ind + node.left
    f.write(prefix)
    if node.node_type:
      f.PushColor(runtime.Color_TypeName)
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

    f.PushColor(runtime.Color_TypeName)
    f.write(node.node_type)
    f.PopColor()

    f.write('\n')
    i = 0
    for name, val in node.fields:
      ind1 = ' ' * (indent+INDENT)
      if isinstance(val, runtime.PrettyArray):  # list field
        name_str = '%s%s: [' % (ind1, name)
        f.write(name_str)
        prefix_len = len(name_str)

        if not _PrintWholeArray(val.children, prefix_len, f, indent, max_col):
          f.write('\n')
          for child in val.children:
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
  # type: (runtime._PrettyBase, ColorOutput, int, int) -> None
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
  if _TrySingleLine(node, single_f, max_col - indent):
    f.WriteRaw(single_f.GetRaw())
    return

  if isinstance(node, runtime.PrettyLeaf):
    f.PushColor(node.e_color)
    f.write(pretty.Str(node.s))
    f.PopColor()

  elif isinstance(node, runtime.PrettyNode):
    _PrintTreeObj(node, f, indent, max_col)

  else:
    raise AssertionError(node)


def _TrySingleLineObj(node, f, max_chars):
  # type: (runtime.PrettyNode, ColorOutput, int) -> bool
  """Print an object on a single line."""
  f.write(node.left)
  if node.abbrev:
    if node.node_type:
      f.PushColor(runtime.Color_TypeName)
      f.write(node.node_type)
      f.PopColor()
      f.write(' ')

    for i, val in enumerate(node.unnamed_fields):
      if i != 0:
        f.write(' ')
      if not _TrySingleLine(val, f, max_chars):
        return False
  else:
    f.PushColor(runtime.Color_TypeName)
    f.write(node.node_type)
    f.PopColor()

    for name, val in node.fields:
      f.write(' %s:' % name)
      if not _TrySingleLine(val, f, max_chars):
        return False

  f.write(node.right)
  return True


def _TrySingleLine(node,  # type: runtime._PrettyBase
                   f,  # type: ColorOutput
                   max_chars,  # type: int
                   ):
  # type: (...) -> bool
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
  if isinstance(node, runtime.PrettyLeaf):
    f.PushColor(node.e_color)
    f.write(pretty.Str(node.s))
    f.PopColor()

  elif isinstance(node, runtime.PrettyArray):  # Can we fit the WHOLE list on the line?
    f.write('[')
    for i, item in enumerate(node.children):
      if i != 0:
        f.write(' ')
      if not _TrySingleLine(item, f, max_chars):
        return False
    f.write(']')

  elif isinstance(node, runtime.PrettyNode):
    return _TrySingleLineObj(node, f, max_chars)

  else:
    raise AssertionError("Unexpected node: %r" % node)
    # mycpp doesn't like __class__
    #raise AssertionError("Unexpected node: %r (%r)" % (node, node.__class__))

  # Take into account the last char.
  num_chars_so_far = f.NumChars()
  if num_chars_so_far > max_chars:
    return False

  return True
