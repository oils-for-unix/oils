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

from asdl import pretty
from asdl import runtime
from core import util
from pylib import cgi


def DetectConsoleOutput(f):
  """Wrapped to auto-detect."""
  if f.isatty():
    return AnsiOutput(f)
  else:
    return TextOutput(f)


class ColorOutput(object):
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
    Write raw data without escaping, and without counting control codes in the
    length.
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
    elif str_type == _SIMPLE_SUM:
      css_class = 'n'
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
_SIMPLE_SUM = 5  # e.g. assign_op = Equal | PlusEqual


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
    elif str_type == _SIMPLE_SUM:
      self.f.write(_YELLOW)
    else:
      raise AssertionError(str_type)

  def PopColor(self):
    self.f.write(_RESET)


#
# Nodes
#


class _PrettyBase(object):
  pass


class _PrettyNode(_PrettyBase):
  """Homogeneous node for pretty-printing."""

  def __init__(self, node_type):
    self.node_type = node_type
    self.fields = []  # list of 2-tuples of (name, _PrettyBase)

    # Custom hooks set abbrev = True and use the nodes below.
    self.abbrev = False
    self.show_node_type = True  # only respected when abbrev is false
    self.left = '('
    self.right = ')'
    self.unnamed_fields = []  # Used by abbreviations

  def __repr__(self):
    return '<_PrettyNode %s %s>' % (self.node_type, self.fields)


class _PrettyLeaf(_PrettyBase):
  """Colored string for pretty-printing."""

  def __init__(self, s, str_type):
    assert isinstance(s, str), s
    self.s = s
    self.str_type = str_type

  def __repr__(self):
    return '<_PrettyLeaf %s %s>' % (self.s, self.str_type)


def _MakePrettySubtree(field_val, desc, abbrev_hook):
  """Given a field value and type descriptor, return a _PrettyBase."""

  if isinstance(desc, runtime.BoolType):
    out_val = _PrettyLeaf('T' if field_val else 'F', _OTHER_LITERAL)

  elif isinstance(desc, runtime.IntType):
    out_val = _PrettyLeaf(str(field_val), _OTHER_LITERAL)

  elif isinstance(desc, runtime.StrType):
    out_val = _PrettyLeaf(field_val, _STRING_LITERAL)

  elif isinstance(desc, runtime.DictType):
    raise AssertionError

  elif isinstance(desc, runtime.SumType):
    if desc.is_simple:
      out_val = _PrettyLeaf(field_val.name, _SIMPLE_SUM)
    else:
      out_val = MakePrettyTree(field_val, abbrev_hook)

  elif isinstance(desc, runtime.CompoundType):
    out_val = MakePrettyTree(field_val, abbrev_hook)

  elif isinstance(desc, runtime.ArrayType):
    out_val = []
    obj_list = field_val
    for item in obj_list:
      t = _MakePrettySubtree(item, desc.desc, abbrev_hook)
      out_val.append(t)

    if not obj_list:  # don't display empty lists
      out_val = None

  elif isinstance(desc, runtime.MaybeType):
    if field_val is None:
      out_val = None
    else:
      out_val = _MakePrettySubtree(field_val, desc.desc, abbrev_hook)

  elif isinstance(desc, runtime.UserType):  # e.g. Id
    out_val = _PrettyLeaf(repr(field_val), _OTHER_TYPE)

  else:
    raise AssertionError('%s %r' % (field_val, desc))

  return out_val


def MakePrettyTree(obj, abbrev_hook=None):
  """The first step of printing: create a homogeneous tree.

  Args:
    obj: runtime.CompoundObj
    abbrev_hook: function to mutate output _PrettyNode
  Returns:
    _PrettyBase
  """
  assert isinstance(obj, runtime.CompoundObj), obj

  class_name = obj.__class__.__name__
  # Hack for constructor names.  We don't know if it is a Product or
  # Constructor here, but product names won't contain '__'.
  out_node = _PrettyNode(class_name.replace('__', '.'))

  for field_name, desc in obj.ASDL_TYPE.GetFields():
    # Always omit spids when abbreviating
    if field_name == 'spids' and abbrev_hook:
      continue

    try:
      field_val = getattr(obj, field_name)
    except AttributeError:
      # This happens when required fields are not initialized, e.g. FuncCall()
      # without setting name.
      raise AssertionError(
          '%s is missing field %r' % (obj.__class__, field_name))

    out_val = _MakePrettySubtree(field_val, desc, abbrev_hook)

    if out_val is not None:
      out_node.fields.append((field_name, out_val))

  # Call user-defined hook to abbreviate compound objects.
  if abbrev_hook:
    abbrev_hook(obj, out_node)

  return out_node


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
      new_indent = indent + INDENT
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

  if isinstance(node, _PrettyLeaf):
    f.PushColor(node.str_type)
    f.write(pretty.Str(node.s))
    f.PopColor()

  elif isinstance(node, _PrettyNode):
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
  if isinstance(node, _PrettyLeaf):
    f.PushColor(node.str_type)
    f.write(pretty.Str(node.s))
    f.PopColor()

  elif isinstance(node, list):  # Can we fit the WHOLE list on the line?
    f.write('[')
    for i, item in enumerate(node):
      if i != 0:
        f.write(' ')
      if not _TrySingleLine(item, f, max_chars):
        return False
    f.write(']')

  elif isinstance(node, _PrettyNode):
    return _TrySingleLineObj(node, f, max_chars)

  else:
    raise AssertionError("Unexpected node: %r (%r)" % (node, node.__class__))

  # Take into account the last char.
  num_chars_so_far = f.NumChars()
  if num_chars_so_far > max_chars:
    return False

  return True
