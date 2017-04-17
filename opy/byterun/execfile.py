"""Execute files of Python code."""

import imp
import os
import sys

from pyvm2 import VirtualMachine


# In Py 2.x, the builtins were in __builtin__
BUILTINS = sys.modules['__builtin__']


def run_code_object(code, args, package=None):
    # Create a module to serve as __main__
    old_main_mod = sys.modules['__main__']
    main_mod = imp.new_module('__main__')
    sys.modules['__main__'] = main_mod
    main_mod.__file__ = args[0]
    if package:
        main_mod.__package__ = package
    main_mod.__builtins__ = BUILTINS

    # Set sys.argv and the first path element properly.
    old_argv = sys.argv
    old_path0 = sys.path[0]
    sys.argv = args
    if package:
        sys.path[0] = ''
    else:
        sys.path[0] = os.path.abspath(os.path.dirname(args[0]))

    vm = VirtualMachine()
    try:
        # Execute the source file.
        vm.run_code(code, f_globals=main_mod.__dict__)
    finally:
        # Restore the old __main__
        sys.modules['__main__'] = old_main_mod

        # Restore the old argv and path
        sys.argv = old_argv
        sys.path[0] = old_path0
