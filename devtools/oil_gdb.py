"""
oil_gdb.py

https://fy.blackhats.net.au/blog/html/2017/08/04/so_you_want_to_script_gdb_with_python.html
"""
from __future__ import print_function

import struct

import gdb

class SimpleCommand(gdb.Command):
    def __init__(self):
        # This registers our class as "simple_command"
        super(SimpleCommand, self).__init__("simple_command", gdb.COMMAND_DATA)

    def invoke(self, arg, from_tty):
        # When we call "simple_command" from gdb, this is the method
        # that will be called.
        print("Hello from simple_command!")

# This registers our class to the gdb runtime at "source" time.
SimpleCommand()


# Following:
# https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/6/html/developer_guide/debuggingprettyprinters

class StrPrinter:
    def __init__(self, val):
        self.val = val

    def to_string(self):
        len_ = self.val['len_']

        # This is a gdb.Value object
        data_ = self.val['data_']
        
        # Make a lazystring out of it
        # https://sourceware.org/gdb/current/onlinedocs/gdb/Values-From-Inferior.html
        # TODO: could try utf-8 too
        return data_.lazy_string('ascii', len_)


class AsdlPrinter(object):
    """Print the variants of a particular ASDL sum type.

    Essentially, this looks at the tag in memory and casts the "super" sum type
    to the variant type.
    """
    def __init__(self, val, variants):
        self.val = val
        self.variants = variants

    def to_string(self):
        # Get address of value and look at first 16 bits
        obj = self.val.dereference()  # location of part_value_t

        # Read the uint16_t tag
        tag_mem = gdb.selected_inferior().read_memory(obj.address, 2)

        # Unpack 2 bytes into an integer
        (tag,) = struct.unpack('H', tag_mem)

        if tag in self.variants:
          typ = gdb.lookup_type(self.variants[tag]).pointer()
        else:
          #pprint(self.variants)
          raise AssertionError('Invalid tag %d' % tag)

        # TODO: I want to also print the tag here, e.g. part_value.String

        v = self.val.cast(typ)
        return v.dereference()


class TypeLookup(object):
  """Return a custom pretty printer based on GDB type information."""

  def __init__(self, sum_type_lookup):
    self.sum_type_lookup = sum_type_lookup

  def __call__(self, val):
    # TODO: 
    # - Tuple{2,3,4} (may be a value, not a pointer)
    # - Dict*

    typ = val.type
    # Str*, etc.
    if typ.code == gdb.TYPE_CODE_PTR:
      target = typ.target()
      #print('target %s' % target)
      #print('target name %r' % target.name)
      #print('target tag %r' % target.tag)

      if target.name == 'Str':
          return StrPrinter(val)

      if target.name in self.sum_type_lookup:
          return AsdlPrinter(val, self.sum_type_lookup[target.name])

    return None


def Preprocess(t):
  """
  Take a list of raw dicts from the ASDL compiler and make a single dict that
  TypeLookup() can use.

  Note: technically this could be done at build time.
  """
  type_lookup = {}
  for (cpp_namespace, tags_to_types) in t:
    for sum_name, d in tags_to_types.items():
      d2 = {}
      for tag, type_name in d.items():
        d2[tag] = '%s::%s' % (cpp_namespace, type_name)
      type_lookup['%s::%s' % (cpp_namespace, sum_name)] = d2
  return type_lookup


# Each of these files defines two variables.  We append them to a global list.
asdl_types = []
gdb.execute('source _devbuild/gen/syntax_asdl_debug.py')
asdl_types.append((cpp_namespace, tags_to_types))
gdb.execute('source _devbuild/gen/runtime_asdl_debug.py')
asdl_types.append((cpp_namespace, tags_to_types))

sum_type_lookup = Preprocess(asdl_types)

#from pprint import pprint
#pprint(type_lookup)


gdb.pretty_printers.append(TypeLookup(sum_type_lookup))
