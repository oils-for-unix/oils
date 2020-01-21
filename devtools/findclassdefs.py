"""
Given a list of module filenames as arguments, and a list of class
names in STDIN (one per line), write out fully qualified names for
each of the classes, if they are defined in one of the given modules.

Used with typeimports.py to auto-add imports when adding type
annotations.
"""
from collections import defaultdict
import re
import sys
import ast

def build_name_module_mapping(filenames):
	name_to_module = defaultdict(list)
	for filename in filenames:
		src = open(filename, 'r').read()
		mod_path = filename.replace('.py', '').replace('/', '.')
		module = ast.parse(src, filename)
		for node in ast.walk(module):
			if isinstance(node, ast.ClassDef):
				name_to_module[node.name].append(mod_path)
	return name_to_module

def main():
	name_to_module = build_name_module_mapping(sys.argv[1:])

	for class_name in sys.stdin:
		class_name = class_name.strip()
		mod_paths = name_to_module[class_name]
		if len(mod_paths) == 1:
			print mod_paths[0] + '.' + class_name

if __name__ == '__main__':
	main()
