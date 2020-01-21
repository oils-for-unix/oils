"""
A very brittle, ad-hoc script to add imports to python modules,
only if they are contained within an "if TYPE_CHECKING" block.  It is
likely to break if given the slightest deviation from expected input.
The modified code is printed to STDOUT.

This is a helper to make adding mypy type annotations more pleasant
(with the end goal of translating python to cpp using mycpp).

  Usage: typeimports.py PYTHON_FILENAME [IMPORT_NAME...]

  where IMPORT_NAME is something like _devbuild.gen.syntax_asdl.command_t
  to be turned into "from _devbuild.gen.syntax_asdl import (command_t, ..."

Assumptions:

* There is a top level 'if TYPE_CHECKING:' statement (if not, this script is a no-op).
  Only imports in this conditional clause are considered.

* There already exist import statements for the relevant modules.  New
  import statements are not added. (This might be worth fixing)

* These imports are of the form "from XXX import (YYY, ZZZ...)",
  though they can be multi-line.

* The IMPORT_NAMES are all valid and well-formed.

Limitations:

* Since this script only adds annotations to the 'if TYPE_CHECKING:'
  block, it will not add imports in the right place if you are adding
  `cast(...)` statements.  You'll probably have to go through
  afterward and move some imports to the top level of the module.
"""

from collections import defaultdict
import sys
import ast
import textwrap


def register_parents(node, parent_map):
	for child in ast.iter_child_nodes(node):
		parent_map[child] = node
		register_parents(child, parent_map)


def replace_slice(orig, start, end, replacement):
	return orig[:start] + replacement + orig[end:]


def add_import(src, module, import_mod, import_names):
	lines = src.splitlines()

	parent_map = {}
	register_parents(module, parent_map)

	for node in ast.walk(module):
		if isinstance(node, ast.ImportFrom):
			parent = parent_map[node]

			if isinstance(parent, ast.If) and isinstance(parent.test, ast.Name) and parent.test.id == 'TYPE_CHECKING':
				if node.module != import_mod:
					continue
				start = node.lineno - 1
				starting_line = lines[start]
				if '(' in starting_line:
					end = start
					while ')' not in lines[end]:
						end += 1
				else:
					end = start

				new_names = [n.name for n in node.names] + import_names
				new_imports = ', '.join(sorted(new_names))
				new_lines = ['  from {} import ('.format(import_mod)] + \
					textwrap.wrap(new_imports, 80, initial_indent='    ', subsequent_indent='    ') +\
					['  )']
				lines = replace_slice(lines, start, end+1, new_lines)
	return '\n'.join(lines)


def main():
	filename = sys.argv[1]
	imports_to_add = sys.argv[2:]
	src = open(filename, 'r').read()

	to_add = defaultdict(list)
	for impname in imports_to_add:
		mod, _, name = impname.rpartition('.')
		to_add[mod].append(name)

	for import_mod, import_names in to_add.items():
		# Repeatedly parsing and adding imports for one module at a
		# time is wasteful, but avoids the necessity of dealing with
		# line numbers shifting.
		module = ast.parse(src, filename)
		src = add_import(src, module, import_mod, import_names)
	compile(src, '', 'exec')
	print src,

if __name__ == '__main__':
	main()
