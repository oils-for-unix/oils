"""
oil_gdb.py

https://fy.blackhats.net.au/blog/html/2017/08/04/so_you_want_to_script_gdb_with_python.html
"""
from __future__ import print_function

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

class value__Printer:
    """
    runtime_asdl::value_t

    _value_str = {
      1: 'value.Undef',
      2: 'value.Str',
      3: 'value.Int',
      4: 'value.MaybeStrArray',
      5: 'value.AssocArray',
      6: 'value.Eggex',
      7: 'value.Obj',
    }
    """
    def __init__(self, val):
        self.val = val

    def to_string(self):
        # TODO: copy below
        pass


class AsdlPrinter(object):
    """
    Print any ASDL type.
    """
    def __init__(self, val, variants):
        self.val = val
        self.variants = variants

    def to_string(self):
        # Get address of value and look at first 16 bits

        obj = self.val.dereference()  # location of part_value_t

        # read the uint16_t tag
        tag_mem = gdb.selected_inferior().read_memory(obj.address, 2)

        # it's little endian
        tag = ord(tag_mem[0])
        #print('tag %r' % tag)

        if tag in self.variants:
          typ = gdb.lookup_type(self.variants[tag]).pointer()
        else:
          raise AssertionError('Invalid tag %d' % tag)

        v = self.val.cast(typ)
        return v.dereference()


class TypeLookup(object):
  """Return a custom pretty printer based on GDB type information.
  """

  def __init__(self, asdl_types):
    self.asdl_types = asdl_types

  def __call__(self, val):
    #print('type %s' % val.type)
    #print('type code %s' % val.type.code)
    #print('type code PTR %s' % gdb.TYPE_CODE_PTR)

    type_name = str(val.type)

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

      if target.name in self.asdl_types:
          return AsdlPrinter(val, self.asdl_types[target.name])

    return None

# Ah OK this works.
# This could be _devbuild/gen/oil_gdb_data.py
# Or I guess one for each ASDL file?
gdb.execute('source devtools/oil_gdb_data.py')

gdb.pretty_printers.append(TypeLookup(asdl_types))
