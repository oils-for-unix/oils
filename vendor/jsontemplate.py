# Copyright (C) 2009 Andy Chu
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Python implementation of json-template.

JSON Template is a minimal and powerful templating language for transforming a
JSON dictionary to arbitrary text.

To use this module, you will typically use the Template constructor, and catch
various exceptions thrown.  You may also want to use the FromFile/FromString
methods, which allow Template constructor options to be embedded in the template
string itself.

Other functions are exposed for tools which may want to process templates.

Unicode
-------

JSON Template can work on unicode strings or byte strings.  The template parser
and expansion loop don't care which type they get.

However, it's up to the caller to ensure that they get *compatible* types.
Python auto-conversion can make this a bit confusing.

If you have a byte string template and a dictionary with byte strings, expansion
will work:

'Hello {name}' +  {name: '\xb5'}  ->  'Hello \xb5'

If you have a unicode template and unicode data in the dictionary, it will work:

u'Hello {name}' +  {name: u'\u00B5'}  ->  u'Hello \u00B5'

If you have a unicode template and byte string data, Python will try to decode
the byte strings using the utf-8 encoding.  This may not be possible, in which
case you'll get a UnicodeDecodeError.

u'Hello {name}' +  {name: 'there'}  ->  'Hello there'
u'Hello {name}' +  {name: '\xb5'}     ->  ERROR: \xb5 is not decodable as ASCII

Mixing types may incur a performance penalty.
"""

__author__ = 'Andy Chu'

__all__ = [
    # Errors
    'Error', 'CompilationError', 'EvaluationError', 'BadFormatter',
    'BadPredicate', 'MissingFormatter', 'ConfigurationError',
    'TemplateSyntaxError', 'UndefinedVariable',
    # API
    'FromString', 'FromFile', 'Template', 'expand', 'Trace', 'FunctionRegistry',
    'MakeTemplateGroup',
    # Function API
    'SIMPLE_FUNC', 'ENHANCED_FUNC']

import StringIO
import pprint
import re
import sys

# For formatters
import cgi  # cgi.escape
import time  # for strftime
import urllib  # for urllib.encode
import urlparse  # for urljoin


class Error(Exception):
  """Base class for all exceptions in this module.

  Thus you can "except jsontemplate.Error: to catch all exceptions thrown by
  this module.
  """

  def __str__(self):
    """This helps people debug their templates.

    If a variable isn't defined, then some context is shown in the traceback.
    TODO: Attach context for other errors.
    """
    if hasattr(self, 'near'):
      return '%s\n\nNear: %s' % (self.args[0], pprint.pformat(self.near))
    else:
      return self.args[0]


class UsageError(Error):
  """Errors in using the API, not a result of compilation or evaluation."""


class CompilationError(Error):
  """Base class for errors that happen during the compilation stage."""


class EvaluationError(Error):
  """Base class for errors that happen when expanding the template.

  This class of errors generally involve the data dictionary or the execution of
  the formatters.
  """
  def __init__(self, msg, original_exc_info=None):
    Error.__init__(self, msg)
    self.original_exc_info = original_exc_info


class BadFormatter(CompilationError):
  """A bad formatter was specified, e.g. {variable|BAD}"""

class BadPredicate(CompilationError):
  """A bad predicate was specified, e.g. {.BAD?}"""

class MissingFormatter(CompilationError):
  """
  Raised when formatters are required, and a variable is missing a formatter.
  """

class ConfigurationError(CompilationError):
  """
  Raised when the Template options are invalid and it can't even be compiled.
  """

class TemplateSyntaxError(CompilationError):
  """Syntax error in the template text."""

class UndefinedVariable(EvaluationError):
  """The template contains a variable name not defined by the data dictionary."""


# The last group is of the form 'name | f1 | f2 ...'
_SECTION_RE = re.compile(r'(repeated)?\s*section\s+(.+)')

# Some formatters and predicates need to look up values in the whole context,
# rather than just the current node.  'Node functions' start with a lowercase
# letter; 'Context functions' start with any other character.
SIMPLE_FUNC, ENHANCED_FUNC = 0, 1

# Templates are a third kind of function, but only for formatters currently
TEMPLATE_FORMATTER = 2


class FunctionRegistry(object):
  """Abstract class for looking up formatters or predicates at compile time.

  Users should implement either Lookup or LookupWithType, and then the
  implementation calls LookupWithType.
  """

  def Lookup(self, user_str):
    """Lookup a function.

    Args:
      user_str: A raw string from the user, which may include uninterpreted
        arguments.  For example, 'pluralize person people' or 'test? admin'

    Returns:
      A 2-tuple of (function, args)
        function: Callable that formats data as a string
        args: Extra arguments to be passed to the function at expansion time
          Should be None to pass NO arguments, since it can pass a 0-tuple too.
    """
    raise NotImplementedError

  def LookupWithType(self, user_str):
    func, args = self.Lookup(user_str)
    # If users need the complexity of FunctionRegistry, then they get the
    # 3-arguments formatter signature (value, context, args)
    return func, args, ENHANCED_FUNC


def _DecideFuncType(user_str):
  """
  By default, formatters/predicates which start with a non-lowercase letter take
  contexts rather than just the cursor.
  """
  if user_str[0].islower():
    return SIMPLE_FUNC
  else:
    return ENHANCED_FUNC


class DictRegistry(FunctionRegistry):
  """Look up functions in a simple dictionary."""

  def __init__(self, func_dict):
    self.func_dict = func_dict

  def LookupWithType(self, user_str):
    return self.func_dict.get(user_str), None, _DecideFuncType(user_str)


class CallableRegistry(FunctionRegistry):
  """Look up functions in a (higher-order) function."""

  def __init__(self, func):
    self.func = func

  def LookupWithType(self, user_str):
    return self.func(user_str), None, _DecideFuncType(user_str)


class PrefixRegistry(FunctionRegistry):
  """Lookup functions with arguments.

  The function name is identified by a prefix.  The character after the prefix,
  usually a space, is considered the argument delimiter (similar to sed/perl's
  s/foo/bar s|foo|bar syntax).
  """

  def __init__(self, functions):
    """
    Args:
      functions: List of 2-tuples (prefix, function), e.g.
      [('pluralize', _Pluralize), ('cycle', _Cycle)]
    """
    self.functions = functions

  def Lookup(self, user_str):
    for prefix, func in self.functions:
      if user_str.startswith(prefix):
        i = len(prefix)

        # Usually a space, but could be something else
        try:
          splitchar = user_str[i]
        except IndexError:
          args = ()  # No arguments
        else:
          args = user_str.split(splitchar)[1:]

        return func, args
    return None, ()


class _TemplateRef(object):
  """A reference from one template to another.

  The _TemplateRef sits statically in the program tree as one of the formatters.
  At runtime, _DoSubstitute calls Resolve() with the group being used.
  """
  def __init__(self, name=None, template=None):
    self.name = name
    self.template = template  # a template that's already been resolved

  def Resolve(self, context):
    if self.template:
      return self.template
    if context.group:
      return context.group.get(self.name)
    else:
      raise EvaluationError(
          "Couldn't find template with name %r (create a template group?)"
          % self.name)


class _TemplateRegistry(FunctionRegistry):
  """Each template owns a _TemplateRegistry.

  LookupWithType always returns a TemplateRef to the template compiler
  (_ProgramBuilder).  At runtime, which may be after MakeTemplateGroup is
  called, the names can be resolved.
  """
  def __init__(self, owner):
    """
    Args:
      owner: The Template instance that owns this formatter.  (There should be
      exactly one)
    """
    self.owner = owner

  def LookupWithType(self, user_str):
    """
    Returns:
      ref: Either a template instance (itself) or _TemplateRef
    """
    prefix = 'template '
    ref = None  # fail the lookup by default
    if user_str.startswith(prefix):
      name = user_str[len(prefix):]
      if name == 'SELF':
        # we can resolve this right away
        ref = _TemplateRef(template=self.owner)  # special value
      else:
        ref = _TemplateRef(name)

    return ref, (), TEMPLATE_FORMATTER


class ChainedRegistry(FunctionRegistry):
  """Look up functions in chain of other FunctionRegistry instances."""

  def __init__(self, registries):
    self.registries = registries

  def LookupWithType(self, user_str):
    for registry in self.registries:
      func, args, func_type = registry.LookupWithType(user_str)
      if func:
        return func, args, func_type

    # Nothing found
    return None, None, SIMPLE_FUNC


class _ProgramBuilder(object):
  """
  Receives method calls from the parser, and constructs a tree of _Section()
  instances.
  """

  def __init__(self, formatters, predicates, template_registry):
    """
    Args:
      formatters: See docstring for _CompileTemplate
      predicates: See docstring for _CompileTemplate
    """
    self.current_section = _Section(None)
    self.stack = [self.current_section]

    # Passing a dictionary or a function is often more convenient than making a
    # FunctionRegistry
    if isinstance(formatters, dict):
      formatters = DictRegistry(formatters)
    elif callable(formatters):
      formatters = CallableRegistry(formatters)

    # default formatters with arguments
    default_formatters = PrefixRegistry([
        ('pluralize', _Pluralize),
        ('cycle', _Cycle),
        # These have to go first because 'strftime' is a prefix of
        # strftime-local/gm!
        ('strftime-local', _StrftimeLocal),  # local
        ('strftime-gm', _StrftimeGm),  # world
        ('strftime', _StrftimeLocal),  # local by default
        ])

    # First consult user formatters, then templates enabled by
    # MakeTemplateGroup, then the default formatters
    self.formatters = ChainedRegistry([
        formatters,
        template_registry,  # returns _TemplateRef instances
        DictRegistry(_DEFAULT_FORMATTERS),
        default_formatters])

    # Same for predicates
    if isinstance(predicates, dict):
      predicates = DictRegistry(predicates)
    elif callable(predicates):
      predicates = CallableRegistry(predicates)

    # default predicates with arguments
    default_predicates = PrefixRegistry([
        ('test', _TestAttribute),
        ('template', _TemplateExists),
        ])

    self.predicates = ChainedRegistry(
        [predicates, DictRegistry(_DEFAULT_PREDICATES), default_predicates])

  def Append(self, statement):
    """
    Args:
      statement: Append a literal
    """
    self.current_section.Append(statement)

  def _GetFormatter(self, format_str):
    """
    The user's formatters are consulted first, then the default formatters.
    """
    formatter, args, func_type = self.formatters.LookupWithType(format_str)
    if formatter:
      return formatter, args, func_type
    else:
      raise BadFormatter('%r is not a valid formatter' % format_str)

  def _GetPredicate(self, pred_str, test_attr=False):
    """
    The user's predicates are consulted first, then the default predicates.
    """
    predicate, args, func_type = self.predicates.LookupWithType(pred_str)
    if predicate:
      pred = predicate, args, func_type
    else:
      # Nicer syntax, {.debug?} is shorthand for {.if test debug}.
      # Currently there is not if/elif chain; just use
      # {.if test debug} {.or test release} {.or} {.end}
      if test_attr:
        assert pred_str.endswith('?')
        # func, args, func_type
        pred = (_TestAttribute, (pred_str[:-1],), ENHANCED_FUNC)
      else:
        raise BadPredicate('%r is not a valid predicate' % pred_str)
    return pred

  def AppendSubstitution(self, name, formatters):
    formatters = [self._GetFormatter(f) for f in formatters]
    self.current_section.Append((_DoSubstitute, (name, formatters)))

  def AppendTemplateSubstitution(self, name):
    # {.template BODY} is semantically something like {$|template BODY}, where $
    # is the root
    formatters = [self._GetFormatter('template ' + name)]
    # None as the name indicates we use the context.Root()
    self.current_section.Append((_DoSubstitute, (None, formatters)))

  def _NewSection(self, func, new_block):
    self.current_section.Append((func, new_block))
    self.stack.append(new_block)
    self.current_section = new_block

  def NewSection(self, token_type, section_name, pre_formatters):
    """For sections or repeated sections."""
    pre_formatters = [self._GetFormatter(f) for f in pre_formatters]

    # TODO: Consider getting rid of this dispatching, and turn _Do* into methods
    if token_type == REPEATED_SECTION_TOKEN:
      new_block = _RepeatedSection(section_name, pre_formatters)
      func = _DoRepeatedSection
    elif token_type == SECTION_TOKEN:
      new_block = _Section(section_name, pre_formatters)
      func = _DoSection
    elif token_type == DEF_TOKEN:
      new_block = _Section(section_name, [])
      func = _DoDef
    else:
      raise AssertionError('Invalid token type %s' % token_type)

    self._NewSection(func, new_block)

  def NewOrClause(self, pred_str):
    """
    {.or ...} Can appear inside predicate blocks or section blocks, with
    slightly different meaning.
    """
    if pred_str:
      pred = self._GetPredicate(pred_str, test_attr=False)
    else:
      pred = None
    self.current_section.NewOrClause(pred)

  def AlternatesWith(self):
    self.current_section.AlternatesWith()

  def NewPredicateSection(self, pred_str, test_attr=False):
    """For chains of predicate clauses."""
    pred = self._GetPredicate(pred_str, test_attr=test_attr)
    block = _PredicateSection()
    block.NewOrClause(pred)

    self._NewSection(_DoPredicates, block)

  def EndSection(self):
    self.stack.pop()
    self.current_section = self.stack[-1]

  def Root(self):
    # It's assumed that we call this at the end of the program
    return self.current_section


class _AbstractSection(object):

  def __init__(self):
    # Pairs of func, args, or a literal string
    self.current_clause = []

  def Append(self, statement):
    """Append a statement to this block."""
    self.current_clause.append(statement)

  def AlternatesWith(self):
    raise TemplateSyntaxError(
        '{.alternates with} can only appear with in {.repeated section ...}')

  def NewOrClause(self, pred_str):
    raise NotImplementedError


class _Section(_AbstractSection):
  """Represents a (repeated) section."""

  def __init__(self, section_name, pre_formatters=[]):
    """
    Args:
      section_name: name given as an argument to the section, None for the root
        section
      pre_formatters: List of formatters to be applied to the data dictinoary
        before the expansion
    """
    _AbstractSection.__init__(self)
    self.section_name = section_name
    self.pre_formatters = pre_formatters

    # Clauses is just a string and a list of statements.
    self.statements = {'default': self.current_clause}

  def __repr__(self):
    return '<Section %s>' % self.section_name

  def Statements(self, clause='default'):
    return self.statements.get(clause, [])

  def NewOrClause(self, pred):
    if pred:
      raise TemplateSyntaxError(
          '{.or} clause only takes a predicate inside predicate blocks')
    self.current_clause = []
    self.statements['or'] = self.current_clause


class _RepeatedSection(_Section):
  """Repeated section is like section, but it supports {.alternates with}"""

  def AlternatesWith(self):
    self.current_clause = []
    self.statements['alternates with'] = self.current_clause


class _PredicateSection(_AbstractSection):
  """Represents a sequence of predicate clauses."""

  def __init__(self):
    _AbstractSection.__init__(self)
    # List of func, statements
    self.clauses = []

  def NewOrClause(self, pred):
    # {.or} always executes if reached
    pred = pred or (lambda x: True, None, SIMPLE_FUNC)  # 3-tuple
    self.current_clause = []
    self.clauses.append((pred, self.current_clause))


class _Frame(object):
  """A stack frame."""

  def __init__(self, context, index=-1):
    # Public attributes
    self.context = context
    self.index = index   # An iteration index.  -1 means we're NOT iterating.

  def __str__(self):
    return 'Frame %s (%s)' % (self.context, self.index)


class _ScopedContext(object):
  """Allows scoped lookup of variables.

  If the variable isn't in the current context, then we search up the stack.
  This object also stores the group.
  """

  def __init__(self, context, undefined_str, group=None):
    """
    Args:
      context: The root context
      undefined_str: See Template() constructor.
      group: Used by the {.if template FOO} predicate, and _DoSubstitute
          which is passed the context.
    """
    self.stack = [_Frame(context)]
    self.undefined_str = undefined_str
    self.group = group  # used by _DoSubstitute?
    self.root = context

  def Root(self):
    """For {.template FOO} substitution."""
    return self.root

  def HasTemplate(self, name):
    if not self.group:  # Could be None?
      return False
    return name in self.group

  def PushSection(self, name, pre_formatters):
    """Given a section name, push it on the top of the stack.

    Returns:
      The new section, or None if there is no such section.
    """
    if name == '@':
      value = self.stack[-1].context
    else:
      top = self.stack[-1].context
      try:
        value = top.get(name)
      except AttributeError:  # no .get()
        raise EvaluationError(
            "Can't get name %r from top value %s" % (name, top))

    # Apply pre-formatters
    for i, (f, args, formatter_type) in enumerate(pre_formatters):
      if formatter_type == ENHANCED_FUNC:
        value = f(value, self, args)
      elif formatter_type == SIMPLE_FUNC:
        value = f(value)
      else:
        assert False, 'Invalid formatter type %r' % formatter_type

    self.stack.append(_Frame(value))
    return value

  def Pop(self):
    self.stack.pop()

  def Next(self):
    """Advance to the next item in a repeated section.

    Raises:
      StopIteration if there are no more elements
    """
    stacktop = self.stack[-1]

    # Now we're iterating -- push a new mutable object onto the stack
    if stacktop.index == -1:
      stacktop = _Frame(None, index=0)
      self.stack.append(stacktop)

    context_array = self.stack[-2].context

    if stacktop.index == len(context_array):
      self.stack.pop()
      raise StopIteration

    stacktop.context = context_array[stacktop.index]
    stacktop.index += 1

    return True  # OK, we mutated the stack

  def _Undefined(self, name):
    if self.undefined_str is None:
      raise UndefinedVariable('%r is not defined' % name)
    else:
      return self.undefined_str

  def _LookUpStack(self, name):
    """Look up the stack for the given name."""
    i = len(self.stack) - 1
    while 1:
      frame = self.stack[i]
      if name == '@index':
        if frame.index != -1:  # -1 is undefined
          return frame.index  # @index is 1-based
      else:
        context = frame.context
        if hasattr(context, 'get'):  # Can't look up names in a list or atom
          try:
            return context[name]
          except KeyError:
            pass

      i -= 1  # Next frame
      if i <= -1:  # Couldn't find it anywhere
        return self._Undefined(name)

  def Lookup(self, name):
    """Get the value associated with a name in the current context.

    The current context could be an dictionary in a list, or a dictionary
    outside a list.

    Args:
      name: name to lookup, e.g. 'foo' or 'foo.bar.baz'

    Returns:
      The value, or self.undefined_str

    Raises:
      UndefinedVariable if self.undefined_str is not set
    """
    if name == '@':
      return self.stack[-1].context

    parts = name.split('.')
    value = self._LookUpStack(parts[0])

    # Now do simple lookups of the rest of the parts
    for part in parts[1:]:
      try:
        value = value[part]
      except (KeyError, TypeError):  # TypeError for non-dictionaries
        return self._Undefined(part)

    return value


def _ToString(x):
  """The default default formatter!."""
  # Some cross-language values for primitives.  This is tested in
  # jsontemplate_test.py.
  if x is None:
    return 'null'
  if isinstance(x, basestring):
    return x
  return pprint.pformat(x)


# NOTE: We could consider making formatters act on strings only avoid this
# repetitiveness.  But I wanted to leave open the possibility of doing stuff
# like {number|increment-by 1}, where formatters take and return integers.
def _Html(x):
  # If it's not string or unicode, make it a string
  if not isinstance(x, basestring):
    x = str(x)
  return cgi.escape(x)


def _HtmlAttrValue(x):
  # If it's not string or unicode, make it a string
  if not isinstance(x, basestring):
    x = str(x)
  return cgi.escape(x, quote=True)


def _AbsUrl(relative_url, context, unused_args):
  """Returns an absolute URL, given the current node as a relative URL.

  Assumes that the context has a value named 'base-url'.  This is a little like
  the HTML <base> tag, but implemented with HTML generation.

  Raises:
    UndefinedVariable if 'base-url' doesn't exist
  """
  # urljoin is flexible about trailing/leading slashes -- it will add or de-dupe
  # them
  return urlparse.urljoin(context.Lookup('base-url'), relative_url)


def _Reverse(x):
  """
  We use this on lists as section pre-formatters; it probably works for
  strings too.
  """
  return list(reversed(x))


def _Pairs(data):
  """dictionary -> list of pairs"""
  keys = sorted(data)
  return [{'@key': k, '@value': data[k]} for k in keys]


# See http://google-ctemplate.googlecode.com/svn/trunk/doc/howto.html for more
# escape types.
#
# Also, we might want to take a look at Django filters.
#
# This is a *public* constant, so that callers can use it construct their own
# formatter lookup dictionaries, and pass them in to Template.
_DEFAULT_FORMATTERS = {
    # Because "html" is often the default formatter, we want to let
    # numbers/boolean/etc. pass through, so we add 'str' first.
    'html': _Html,

    # The 'htmltag' name is deprecated.  The html-attr-value name is preferred
    # because it can be read with "as":
    #   {url|html-attr-value} means:
    #   "substitute 'url' as an HTML attribute value"
    'html-attr-value': _HtmlAttrValue,
    'htmltag': _HtmlAttrValue,

    'raw': lambda x: x,
    # Used for the length of a list.  Can be used for the size of a dictionary
    # too, though I haven't run into that use case.
    'size': lambda value: str(len(value)),

    # The argument is a dictionary, and we get a a=1&b=2 string back.
    'url-params': lambda x: urllib.urlencode(x, doseq=True),

    # The argument is an atom, and it takes 'Search query?' -> 'Search+query%3F'
    'url-param-value': urllib.quote_plus,  # param is an atom

    # The default formatter, when no other default is specifier.  For debugging,
    # this could be lambda x: json.dumps(x, indent=2), but here we want to be
    # compatible to Python 2.4.
    'str': _ToString,
    # Python-specific representation for safely debugging any value as an ASCII
    # string (unicode can cause issues when using 'str')
    'repr': repr,

    'upper': lambda x: x.upper(),
    'lower': lambda x: x.lower(),

    # Just show a plain URL on an HTML page (without anchor text).
    'plain-url': lambda x: '<a href="%s">%s</a>' % (
        cgi.escape(x, quote=True), cgi.escape(x)),

    # A context formatter
    'AbsUrl': _AbsUrl,

    # Placeholders for "standard names".  We're not including them by default
    # since they require additional dependencies.  We can provide a part of the
    # "lookup chain" in formatters.py for people people want the dependency.

    # 'json' formats arbitrary data dictionary nodes as JSON strings.  'json'
    # and 'js-string' are identical (since a JavaScript string *is* JSON).  The
    # latter is meant to be serve as extra documentation when you want a string
    # argument only, which is a common case.
    'json': None,
    'js-string': None,

    'reverse': _Reverse,

    # Given a dictinonary, returns a *list* of key-value pairs.  Used for
    # section formatters.  See jsontemplate_test.py for usage.
    #
    # The name "pairs" is meant to be language-independent, so it makes sense
    # in JavaScript, etc.
    'pairs': _Pairs,
    }


def _Pluralize(value, unused_context, args):
  """Formatter to pluralize words."""

  if len(args) == 0:
    s, p = '', 's'
  elif len(args) == 1:
    s, p = '', args[0]
  elif len(args) == 2:
    s, p = args
  else:
    # Should have been checked at compile time
    raise AssertionError

  if value > 1:
    return p
  else:
    return s


def _Cycle(value, unused_context, args):
  """Cycle between various values on consecutive integers."""
  # @index starts from 1, so used 1-based indexing
  return args[(value - 1) % len(args)]


def _StrftimeHelper(args, time_tuple):
  try:
    format_str = args[0]
  except IndexError:
    # If no format string, use some reasonable text format
    return time.asctime(time_tuple)
  else:
    return time.strftime(format_str, time_tuple)


def _StrftimeGm(value, unused_context, args):
  """Convert a timestamp in seconds to a string based on the format string.

  Returns GM time.
  """
  time_tuple = time.gmtime(value)
  return _StrftimeHelper(args, time_tuple)


def _StrftimeLocal(value, unused_context, args):
  """Convert a timestamp in seconds to a string based on the format string.

  Returns local time.
  """
  time_tuple = time.localtime(value)
  return _StrftimeHelper(args, time_tuple)


def _IsDebugMode(unused_value, context, unused_args):
  return _TestAttribute(unused_value, context, ('debug',))


def _TestAttribute(unused_value, context, args):
  """Cycle between various values on consecutive integers."""
  try:
    name = args[0]  # can used dotted syntax too, e.g. 'foo.bar'
  except IndexError:
    raise EvaluationError('The "test" predicate requires an argument.')
  try:
    return bool(context.Lookup(name))
  except UndefinedVariable:
    return False


def _TemplateExists(unused_value, context, args):
  """Returns whether the given name is in the current Template's template group."""
  try:
    name = args[0]
  except IndexError:
    raise EvaluationError('The "template" predicate requires an argument.')
  return context.HasTemplate(name)


_SINGULAR = lambda x: x == 1
_PLURAL = lambda x: x > 1

_DEFAULT_PREDICATES = {
    # OLD, for backward compatibility: these are discouraged
    'singular?': _SINGULAR,
    'plural?': _PLURAL,
    'Debug?': _IsDebugMode,  # Also OLD

    'singular': _SINGULAR,
    'plural': _PLURAL,
    }


def SplitMeta(meta):
  """Split and validate metacharacters.

  Example: '{}' -> ('{', '}')

  This is public so the syntax highlighter and other tools can use it.
  """
  n = len(meta)
  if n % 2 == 1:
    raise ConfigurationError(
        '%r has an odd number of metacharacters' % meta)
  return meta[:n/2], meta[n/2:]


_token_re_cache = {}

def MakeTokenRegex(meta_left, meta_right):
  """Return a (compiled) regular expression for tokenization.

  Args:
    meta_left, meta_right: e.g. '{' and '}'

  - The regular expressions are memoized.
  - This function is public so the syntax highlighter can use it.
  """
  key = meta_left, meta_right
  if key not in _token_re_cache:
    # - Need () grouping for re.split
    # - The first character must be a non-space.  This allows us to ignore
    # literals like function() { return 1; } when
    # - There must be at least one (non-space) character inside {}
    _token_re_cache[key] = re.compile(
        r'(' +
        re.escape(meta_left) +
        r'\S.*?' +
        re.escape(meta_right) +
        r')')
  return _token_re_cache[key]


# Examples:

( LITERAL_TOKEN,  # "Hi"
  META_LITERAL_TOKEN,  # {.space}, etc.

  SUBST_TOKEN,  # {var|html}
  SECTION_TOKEN,  # {.section name}
  REPEATED_SECTION_TOKEN,  # {.repeated section name}
  PREDICATE_TOKEN,  # {.predicate?}
  IF_TOKEN,  # {.if predicate}
  ALTERNATES_TOKEN,  # {.or}
  OR_TOKEN,  # {.or}
  END_TOKEN,  # {.end}

  SUBST_TEMPLATE_TOKEN,  # {.template TITLE}
  DEF_TOKEN,  # {.define TITLE}

  COMMENT_BEGIN_TOKEN,  # {##BEGIN}
  COMMENT_END_TOKEN,  # {##END}
  ) = range(14)

COMMENT_BEGIN = '##BEGIN'
COMMENT_END = '##END'

OPTION_STRIP_LINE = '.OPTION strip-line'
OPTION_END = '.END'


def _MatchDirective(token):
  """Helper function for matching certain directives."""
  # Tokens below must start with '.'
  if token.startswith('.'):
    token = token[1:]
  else:
    return None, None

  if token == 'end':
    return END_TOKEN, None

  if token == 'alternates with':
    return ALTERNATES_TOKEN, token

  if token.startswith('or'):
    if token.strip() == 'or':
      return OR_TOKEN, None
    else:
      pred_str = token[2:].strip()
      return OR_TOKEN, pred_str

  match = _SECTION_RE.match(token)
  if match:
    repeated, section_name = match.groups()
    if repeated:
      return REPEATED_SECTION_TOKEN, section_name
    else:
      return SECTION_TOKEN, section_name

  if token.startswith('template '):
    return SUBST_TEMPLATE_TOKEN, token[9:].strip()
  if token.startswith('define '):
    return DEF_TOKEN, token[7:].strip()

  if token.startswith('if '):
    return IF_TOKEN, token[3:].strip()
  if token.endswith('?'):
    return PREDICATE_TOKEN, token

  return None, None  # no match


def _Tokenize(template_str, meta_left, meta_right, whitespace):
  """Yields tokens, which are 2-tuples (TOKEN_TYPE, token_string)."""

  trimlen = len(meta_left)
  token_re = MakeTokenRegex(meta_left, meta_right)
  do_strip = (whitespace == 'strip-line')  # Do this outside loop
  do_strip_part = False

  for line in template_str.splitlines(True):  # retain newlines
    if do_strip or do_strip_part:
      line = line.strip()

    tokens = token_re.split(line)

    # Check for a special case first.  If a comment or "block" directive is on a
    # line by itself (with only space surrounding it), then the space is
    # omitted.  For simplicity, we don't handle the case where we have 2
    # directives, say '{.end} # {#comment}' on a line.
    if len(tokens) == 3:
      # ''.isspace() == False, so work around that
      if (tokens[0].isspace() or not tokens[0]) and \
         (tokens[2].isspace() or not tokens[2]):
        token = tokens[1][trimlen : -trimlen]

        # Check the ones that begin with ## before #
        if token == COMMENT_BEGIN:
          yield COMMENT_BEGIN_TOKEN, None
          continue
        if token == COMMENT_END:
          yield COMMENT_END_TOKEN, None
          continue
        if token == OPTION_STRIP_LINE:
          do_strip_part = True
          continue
        if token == OPTION_END:
          do_strip_part = False
          continue

        if token.startswith('#'):
          continue  # The whole line is omitted

        token_type, token = _MatchDirective(token)
        if token_type is not None:
          yield token_type, token  # Only yield the token, not space
          continue

    # The line isn't special; process it normally.
    for i, token in enumerate(tokens):
      if i % 2 == 0:
        yield LITERAL_TOKEN, token

      else:  # It's a "directive" in metachracters
        assert token.startswith(meta_left), repr(token)
        assert token.endswith(meta_right), repr(token)
        token = token[trimlen : -trimlen]

        # Check the ones that begin with ## before #
        if token == COMMENT_BEGIN:
          yield COMMENT_BEGIN_TOKEN, None
          continue
        if token == COMMENT_END:
          yield COMMENT_END_TOKEN, None
          continue
        if token == OPTION_STRIP_LINE:
          do_strip_part = True
          continue
        if token == OPTION_END:
          do_strip_part = False
          continue

        # A single-line comment
        if token.startswith('#'):
          continue

        if token.startswith('.'):
          literal = {
              '.meta-left': meta_left,
              '.meta-right': meta_right,
              '.space': ' ',
              '.tab': '\t',
              '.newline': '\n',
              }.get(token)

          if literal is not None:
            yield META_LITERAL_TOKEN, literal
            continue

          token_type, token = _MatchDirective(token)
          if token_type is not None:
            yield token_type, token

        else:  # Now we know the directive is a substitution.
          yield SUBST_TOKEN, token


def _CompileTemplate(
    template_str, builder, meta='{}', format_char='|', default_formatter='str',
    whitespace='smart'):
  """Compile the template string, calling methods on the 'program builder'.

  Args:
    template_str: The template string.  It should not have any compilation
        options in the header -- those are parsed by FromString/FromFile

    builder: The interface of _ProgramBuilder isn't fixed.  Use at your own
        risk.

    meta: The metacharacters to use, e.g. '{}', '[]'.

    default_formatter: The formatter to use for substitutions that are missing a
        formatter.  The 'str' formatter the "default default" -- it just tries
        to convert the context value to a string in some unspecified manner.

    whitespace: 'smart' or 'strip-line'.  In smart mode, if a directive is alone
        on a line, with only whitespace on either side, then the whitespace is
        removed.  In 'strip-line' mode, every line is stripped of its
        leading and trailing whitespace.

  Returns:
    The compiled program (obtained from the builder)

  Raises:
    The various subclasses of CompilationError.  For example, if
    default_formatter=None, and a variable is missing a formatter, then
    MissingFormatter is raised.

  This function is public so it can be used by other tools, e.g. a syntax
  checking tool run before submitting a template to source control.
  """
  meta_left, meta_right = SplitMeta(meta)

  # : is meant to look like Python 3000 formatting {foo:.3f}.  According to
  # PEP 3101, that's also what .NET uses.
  # | is more readable, but, more importantly, reminiscent of pipes, which is
  # useful for multiple formatters, e.g. {name|js-string|html}
  if format_char not in (':', '|'):
    raise ConfigurationError(
        'Only format characters : and | are accepted (got %r)' % format_char)

  if whitespace not in ('smart', 'strip-line'):
    raise ConfigurationError('Invalid whitespace mode %r' % whitespace)

  # If we go to -1, then we got too many {end}.  If end at 1, then we're missing
  # an {end}.
  balance_counter = 0
  comment_counter = 0  # ditto for ##BEGIN/##END

  has_defines = False

  for token_type, token in _Tokenize(template_str, meta_left, meta_right,
                                     whitespace):
    if token_type == COMMENT_BEGIN_TOKEN:
      comment_counter += 1
      continue
    if token_type == COMMENT_END_TOKEN:
      comment_counter -= 1
      if comment_counter < 0:
        raise CompilationError('Got too many ##END markers')
      continue
    # Don't process any tokens
    if comment_counter > 0:
      continue

    if token_type in (LITERAL_TOKEN, META_LITERAL_TOKEN):
      if token:
        builder.Append(token)
      continue

    if token_type in (SECTION_TOKEN, REPEATED_SECTION_TOKEN, DEF_TOKEN):
      parts = [p.strip() for p in token.split(format_char)]
      if len(parts) == 1:
        name = parts[0]
        formatters = []
      else:
        name = parts[0]
        formatters = parts[1:]
      builder.NewSection(token_type, name, formatters)
      balance_counter += 1
      if token_type == DEF_TOKEN:
        has_defines = True
      continue

    if token_type == PREDICATE_TOKEN:
      # {.attr?} lookups
      builder.NewPredicateSection(token, test_attr=True)
      balance_counter += 1
      continue

    if token_type == IF_TOKEN:
      builder.NewPredicateSection(token, test_attr=False)
      balance_counter += 1
      continue

    if token_type == OR_TOKEN:
      builder.NewOrClause(token)
      continue

    if token_type == ALTERNATES_TOKEN:
      builder.AlternatesWith()
      continue

    if token_type == END_TOKEN:
      balance_counter -= 1
      if balance_counter < 0:
        # TODO: Show some context for errors
        raise TemplateSyntaxError(
            'Got too many %send%s statements.  You may have mistyped an '
            "earlier 'section' or 'repeated section' directive."
            % (meta_left, meta_right))
      builder.EndSection()
      continue

    if token_type == SUBST_TOKEN:
      parts = [p.strip() for p in token.split(format_char)]
      if len(parts) == 1:
        if default_formatter is None:
          raise MissingFormatter('This template requires explicit formatters.')
        # If no formatter is specified, the default is the 'str' formatter,
        # which the user can define however they desire.
        name = token
        formatters = [default_formatter]
      else:
        name = parts[0]
        formatters = parts[1:]

      builder.AppendSubstitution(name, formatters)
      continue

    if token_type == SUBST_TEMPLATE_TOKEN:
      # no formatters
      builder.AppendTemplateSubstitution(token)
      continue

  if balance_counter != 0:
    raise TemplateSyntaxError('Got too few %send%s statements' %
        (meta_left, meta_right))
  if comment_counter != 0:
    raise CompilationError('Got %d more {##BEGIN}s than {##END}s' % comment_counter)

  return builder.Root(), has_defines


_OPTION_RE = re.compile(r'^([a-zA-Z\-]+):\s*(.*)')
_OPTION_NAMES = ['meta', 'format-char', 'default-formatter', 'undefined-str',
                 'whitespace']


def FromString(s, **kwargs):
  """Like FromFile, but takes a string."""

  f = StringIO.StringIO(s)
  return FromFile(f, **kwargs)


def FromFile(f, more_formatters=lambda x: None, more_predicates=lambda x: None,
             _constructor=None):
  """Parse a template from a file, using a simple file format.

  This is useful when you want to include template options in a data file,
  rather than in the source code.

  The format is similar to HTTP or E-mail headers.  The first lines of the file
  can specify template options, such as the metacharacters to use.  One blank
  line must separate the options from the template body.

  Example:

    default-formatter: none
    meta: {{}}
    format-char: :
    <blank line required>
    Template goes here: {{variable:html}}

  Args:
    f: A file handle to read from.  Caller is responsible for opening and
    closing it.
  """
  _constructor = _constructor or Template

  options = {}

  # Parse lines until the first one that doesn't look like an option
  while 1:
    line = f.readline()
    match = _OPTION_RE.match(line)
    if match:
      name, value = match.group(1), match.group(2)

      # Accept something like 'Default-Formatter: raw'.  This syntax is like
      # HTTP/E-mail headers.
      name = name.lower()
      # In Python 2.4, kwargs must be plain strings
      name = name.encode('utf-8')

      if name in _OPTION_NAMES:
        name = name.replace('-', '_')
        value = value.strip()
        if name == 'default_formatter' and value.lower() == 'none':
          value = None
        options[name] = value
      else:
        break
    else:
      break

  if options:
    if line.strip():
      raise CompilationError(
          'Must be one blank line between template options and body (got %r)'
          % line)
    body = f.read()
  else:
    # There were no options, so no blank line is necessary.
    body = line + f.read()

  return _constructor(body,
                      more_formatters=more_formatters,
                      more_predicates=more_predicates,
                      **options)


class Template(object):
  """Represents a compiled template.

  Like many template systems, the template string is compiled into a program,
  and then it can be expanded any number of times.  For example, in a web app,
  you can compile the templates once at server startup, and use the expand()
  method at request handling time.  expand() uses the compiled representation.

  There are various options for controlling parsing -- see _CompileTemplate.
  Don't go crazy with metacharacters.  {}, [], {{}} or <> should cover nearly
  any circumstance, e.g. generating HTML, CSS XML, JavaScript, C programs, text
  files, etc.
  """

  def __init__(self, template_str,
               more_formatters=lambda x: None,
               more_predicates=lambda x: None,
               undefined_str=None,
               **compile_options):
    """
    Args:
      template_str: The template string.

      more_formatters:
          Something that can map format strings to formatter functions.  One of:
          - A plain dictionary of names -> functions  e.g. {'html': cgi.escape}
          - A higher-order function which takes format strings and returns
            formatter functions.  Useful for when formatters have parsed
            arguments.
          - A FunctionRegistry instance, giving the most control.  This allows
            formatters which takes contexts as well.

      more_predicates:
          Like more_formatters, but for predicates.

      undefined_str: A string to appear in the output when a variable to be
          substituted is missing.  If None, UndefinedVariable is raised.
          (Note: This is not really a compilation option, because affects
          template expansion rather than compilation.  Nonetheless we make it a
          constructor argument rather than an .expand() argument for
          simplicity.)

    It also accepts all the compile options that _CompileTemplate does.
    """
    r = _TemplateRegistry(self)
    self.undefined_str = undefined_str
    self.group = {}  # optionally updated by _UpdateTemplateGroup
    builder = _ProgramBuilder(more_formatters, more_predicates, r)
    # None used by _FromSection
    if template_str is not None:
      self._program, self.has_defines = _CompileTemplate(
          template_str, builder, **compile_options)
      self.group = _MakeGroupFromRootSection(self._program, self.undefined_str)

  @staticmethod
  def _FromSection(section, group, undefined_str):
    t = Template(None, undefined_str=undefined_str)
    t._program = section
    t.has_defines = False
    # This "subtemplate" needs the group too for its own references
    t.group = group
    return t

  def _Statements(self):
    # for execute_with_style
    return self._program.Statements()

  def _UpdateTemplateGroup(self, group):
    """Allow this template to reference templates in the group.

    Args:
      group: dictionary of template name -> compiled Template instance
    """
    # TODO: Re-enable when Poly is converted
    #if self.has_defines:
    #  raise UsageError(
    #      "Can't make a template group out of a template with {.define}.")
    bad = []
    for name in group:
      if name in self.group:
        bad.append(name)
    if bad:
      raise UsageError(
          "This template already has these named templates defined: %s" % bad)
    self.group.update(group)

  def _CheckRefs(self):
    """Check that the template names referenced in this template exist."""
    # TODO: Implement this.
    # This is called by MakeTemplateGroup.
    # We would walk the program Statements() tree, look for name=None
    # substitutions, with a template formatter, and call Resolve().

  #
  # Public API
  #

  def execute(self, data_dict, callback, group=None, trace=None):
    """Low level method to expand the template piece by piece.

    Args:
      data_dict: The JSON data dictionary.
      callback: A callback which should be called with each expanded token.
      group: Dictionary of name -> Template instance (for styles)

    Example: You can pass 'f.write' as the callback to write directly to a file
    handle.
    """
    # First try the passed in version, then the one set by _UpdateTemplateGroup.
    # May be None.  Only one of these should be set.
    group = group or self.group
    context = _ScopedContext(data_dict, self.undefined_str, group=group)
    _Execute(self._program.Statements(), context, callback, trace)

  render = execute  # Alias for backward compatibility

  def expand(self, *args, **kwargs):
    """Expands the template with the given data dictionary, returning a string.

    This is a small wrapper around execute(), and is the most convenient
    interface.

    Args:
      data_dict: The JSON data dictionary.  Like the builtin dict() constructor,
          it can take a single dictionary as a positional argument, or arbitrary
          keyword arguments.
      trace: Trace object for debugging
      style: Template instance to be treated as a style for this template (the
          "outside")

    Returns:
      The return value could be a str() or unicode() instance, depending on the
      the type of the template string passed in, and what the types the strings
      in the dictionary are.
    """
    if args:
      if len(args) == 1:
        data_dict = args[0]
        trace = kwargs.get('trace')
        style = kwargs.get('style')
        group = kwargs.get('group')
      else:
        raise TypeError(
            'expand() only takes 1 positional argument (got %s)' % args)
    else:
      # NOTE: A problem with this style is that passing invalid kwargs is
      # silently ignored.  It should be expand_with(foo=bar)

      data_dict = kwargs
      trace = None  # Can't use trace= with the kwargs style
      style = None
      group = None

    # Try the argument first, then the thing set by MakeTemplateGroup
    g = group or self.group

    tokens = []
    if style:
      style.execute(data_dict, tokens.append, group=g, trace=trace)
    else:
      # Needs a group to reference its OWN {.define}s
      self.execute(data_dict, tokens.append, group=g, trace=trace)

    return JoinTokens(tokens)

  def tokenstream(self, data_dict):
    """Yields a list of tokens resulting from expansion.

    This may be useful for WSGI apps.  NOTE: In the current implementation, the
    entire expanded template must be stored memory.

    NOTE: This is a generator, but JavaScript doesn't have generators.
    """
    tokens = []
    self.execute(data_dict, tokens.append)
    for token in tokens:
      yield token


class Trace(object):
  """Trace of execution for JSON Template.

  This object should be passed into the execute/expand() function.

  Useful for debugging, especially for templates which reference other
  templates.
  """
  def __init__(self):
    # Public mutable attributes
    self.exec_depth = 0
    self.template_depth = 0
    self.stack = []

  def Push(self, obj):
    self.stack.append(obj)

  def Pop(self):
    self.stack.pop()

  def __str__(self):
    return 'Trace %s %s' % (self.exec_depth, self.template_depth)


def _MakeGroupFromRootSection(root_section, undefined_str):
  """Construct a dictionary { template name -> Template() instance }

  Args:
    root_section: _Section instance -- root of the original parse tree
  """
  group = {}
  for statement in root_section.Statements():
    if isinstance(statement, basestring):
      continue
    func, args = statement
    # here the function acts as ID for the block type
    if func is _DoDef and isinstance(args, _Section):
      section = args
      # Construct a Template instance from a this _Section subtree
      t = Template._FromSection(section, group, undefined_str)
      group[section.section_name] = t
  return group


def MakeTemplateGroup(group):
  """Wire templates together so that they can reference each other by name.

  This is a public API.

  The templates becomes formatters with the 'template' prefix.  For example:
  {var|template NAME} formats the node 'var' with the template 'NAME'

  Templates may be mutually recursive.

  This function *mutates* all the templates, so you shouldn't call it multiple
  times on a single Template() instance.  It's possible to put a single template
  in multiple groups by creating multiple Template() instances from it.

  Args:
    group: dictionary of template name -> compiled Template instance
  """
  # mutate all of the templates so that they can reference each other
  for t in group.itervalues():
    t._UpdateTemplateGroup(group)
    #t._CheckRefs()


def JoinTokens(tokens):
  """Join tokens (which may be a mix of unicode and str values).

  See notes on unicode at the top.  This function allows mixing encoded utf-8
  byte string tokens with unicode tokens.  (Python's default encoding is ASCII,
  and we don't want to change that.)

  We also want to support pure byte strings, so we can't get rid of the
  try/except.  Two tries necessary.

  If someone really wanted to use another encoding, they could monkey patch
  jsontemplate.JoinTokens (this function).
  """
  try:
    return ''.join(tokens)
  except UnicodeDecodeError:
    # This can still raise UnicodeDecodeError if that data isn't utf-8.
    return ''.join(t.decode('utf-8') for t in tokens)


def _DoRepeatedSection(args, context, callback, trace):
  """{.repeated section foo}"""

  block = args

  items = context.PushSection(block.section_name, block.pre_formatters)
  if items:
    if not isinstance(items, list):
      raise EvaluationError('Expected a list; got %s' % type(items))

    last_index = len(items) - 1
    statements = block.Statements()
    alt_statements = block.Statements('alternates with')
    try:
      i = 0
      while True:
        context.Next()
        # Execute the statements in the block for every item in the list.
        # Execute the alternate block on every iteration except the last.  Each
        # item could be an atom (string, integer, etc.) or a dictionary.
        _Execute(statements, context, callback, trace)
        if i != last_index:
          _Execute(alt_statements, context, callback, trace)
        i += 1
    except StopIteration:
      pass

  else:
    _Execute(block.Statements('or'), context, callback, trace)

  context.Pop()


def _DoSection(args, context, callback, trace):
  """{.section foo}"""
  block = args
  # If a section present and "true", push the dictionary onto the stack as the
  # new context, and show it
  if context.PushSection(block.section_name, block.pre_formatters):
    _Execute(block.Statements(), context, callback, trace)
    context.Pop()
  else:  # missing or "false" -- show the {.or} section
    context.Pop()
    _Execute(block.Statements('or'), context, callback, trace)


def _DoPredicates(args, context, callback, trace):
  """{.predicate?}

  Here we execute the first clause that evaluates to true, and then stop.
  """
  block = args
  value = context.Lookup('@')
  for (predicate, args, func_type), statements in block.clauses:
    if func_type == ENHANCED_FUNC:
      do_clause = predicate(value, context, args)
    else:
      do_clause = predicate(value)

    if do_clause:
      if trace: trace.Push(predicate)
      _Execute(statements, context, callback, trace)
      if trace: trace.Pop()
      break


def _DoDef(args, context, callback, trace):
  """{.define TITLE}"""
  # We do nothing here -- the block is parsed into the template tree, turned
  # into a Template() instance, and then the template is called as a formatter
  # in _DoSubstitute.


def _DoSubstitute(args, context, callback, trace):
  """Variable substitution, i.e. {foo}

  We also implement template formatters here, i.e.  {foo|template bar} as well
  as {.template FOO} for templates that operate on the root of the data dict
  rather than a subtree.
  """
  name, formatters = args

  if name is None:
    value = context.Root()  # don't use the cursor
  else:
    try:
      value = context.Lookup(name)
    except TypeError, e:
      raise EvaluationError(
          'Error evaluating %r in context %r: %r' % (name, context, e))

  last_index = len(formatters) - 1
  for i, (f, args, formatter_type) in enumerate(formatters):
    try:
      if formatter_type == TEMPLATE_FORMATTER:
        template = f.Resolve(context)
        if i == last_index:
          # In order to keep less template output in memory, we can just let the
          # other template write to our callback directly, and then stop.
          template.execute(value, callback, trace=trace)
          return  # EARLY RETURN
        else:
          # We have more formatters to apply, so explicitly construct 'value'
          tokens = []
          template.execute(value, tokens.append, trace=trace)
          value = JoinTokens(tokens)

      elif formatter_type == ENHANCED_FUNC:
        value = f(value, context, args)

      elif formatter_type == SIMPLE_FUNC:
        value = f(value)

      else:
        assert False, 'Invalid formatter type %r' % formatter_type

    except (KeyboardInterrupt, EvaluationError):
      # Don't "wrap" recursive EvaluationErrors
      raise

    except Exception, e:
      if formatter_type == TEMPLATE_FORMATTER:
        raise  # in this case we want to see the original exception
      raise EvaluationError(
          'Formatting name %r, value %r with formatter %s raised exception: %r '
          '-- see e.original_exc_info' % (name, value, f, e),
          original_exc_info=sys.exc_info())

  # TODO: Require a string/unicode instance here?
  if value is None:
    raise EvaluationError('Evaluating %r gave None value' % name)
  callback(value)


def _Execute(statements, context, callback, trace):
  """Execute a bunch of template statements in a ScopedContext.

  Args:
    callback: Strings are "written" to this callback function.
    trace: Trace object, or None

  This is called in a mutually recursive fashion.
  """
  # Every time we call _Execute, increase this depth
  if trace:
    trace.exec_depth += 1
  for i, statement in enumerate(statements):
    if isinstance(statement, basestring):
      callback(statement)
    else:
      # In the case of a substitution, args is a pair (name, formatters).
      # In the case of a section, it's a _Section instance.
      try:
        func, args = statement
        func(args, context, callback, trace)
      except UndefinedVariable, e:
        # Show context for statements
        start = max(0, i-3)
        end = i+3
        e.near = statements[start:end]
        e.trace = trace  # Attach caller's trace (could be None)
        raise


def expand(template_str, dictionary, **kwargs):
  """Free function to expands a template string with a data dictionary.

  This is useful for cases where you don't care about saving the result of
  compilation (similar to re.match('.*', s) vs DOT_STAR.match(s))
  """
  t = Template(template_str, **kwargs)
  return t.expand(dictionary)


###
# TODO: DELETE
###
def _FlattenToCallback(tokens, callback):
  """Takes a nested list structure and flattens it.

  ['a', ['b', 'c']] -> callback('a'); callback('b'); callback('c');
  """
  for t in tokens:
    if isinstance(t, basestring):
      callback(t)
    else:
      _FlattenToCallback(t, callback)

###
# TODO: DELETE execute_with_style_LEGACY after old apps cleaned up
####
def execute_with_style_LEGACY(template, style, data, callback, body_subtree='body'):
  """OBSOLETE old API."""
  try:
    body_data = data[body_subtree]
  except KeyError:
    raise EvaluationError('Data dictionary has no subtree %r' % body_subtree)
  tokens_body = []
  template.execute(body_data, tokens_body.append)
  data[body_subtree] = tokens_body
  tokens = []
  style.execute(data, tokens.append)
  _FlattenToCallback(tokens, callback)


def expand_with_style(template, style, data, body_subtree='body'):
  """Expand a data dictionary with a template AND a style.

  DEPRECATED -- Remove this entire function in favor of expand(d, style=style)

  A style is a Template instance that factors out the common strings in several
  "body" templates.

  Args:
    template: Template instance for the inner "page content"
    style: Template instance for the outer "page style"
    data: Data dictionary, with a 'body' key (or body_subtree
  """
  if template.has_defines:
    return template.expand(data, style=style)
  else:
    tokens = []
    execute_with_style_LEGACY(template, style, data, tokens.append,
                              body_subtree=body_subtree)
    return JoinTokens(tokens)
