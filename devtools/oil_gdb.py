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


class part_value__Printer:
    """
    _part_value_str = {
      1: 'part_value.String',
      2: 'part_value.Array',
    }
    """
    def __init__(self, val):
        self.val = val

    def to_string(self):
        # Get address of value and look at first 16 bits

        obj = self.val.dereference()  # location of part_value_t

        # read the uint16_t tag
        tag_mem = gdb.selected_inferior().read_memory(obj.address, 2)

        # it's little endian
        tag = ord(tag_mem[0])
        #print('tag %r' % tag)

        if tag == 1:
          typ = gdb.lookup_type('runtime_asdl::part_value__String').pointer()
        elif tag == 2:
          typ = gdb.lookup_type('runtime_asdl::part_value__Array').pointer()
        else:
          raise AssertionError('Invalid tag %d', tag)

        v = self.val.cast(typ)
        return v.dereference()


def lookup_type(val):
    if str(val.type) == 'Str *':
        return StrPrinter(val)
    #if str(val.type) == 'runtime_asdl::value_t *':
    #    return value__Printer(val)
    if str(val.type) == 'runtime_asdl::part_value_t *':
        return part_value__Printer(val)
    return None

gdb.pretty_printers.append(lookup_type)
