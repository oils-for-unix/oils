#!/usr/bin/env bash
#
# Demo of word evaluation.
#
# Usage:
#   ./hard.sh <function name>
#
# Bug with the current algorithm: IFS=\\

set -- 'a*b' 'c d'
typeset -a myarray
myarray=('w x' 'y*z', 'bin')
space=' '
glob='*h b*'  # anything that ends with h, then anything that begins with b

spec/bin/argv.py -"$@"-$space-"$space-${myarray[@]}"/$glob

# ['-a b', 'c d-', '- -w x', 'y z,', 'bin/opypy-osh', 'bin/osh', 'bin/sh', 'benchmarks', 'bin', 'build']

# I have a single word.
# I evaluate all the parts:
#
# "$@" -> ArrayPartValue
# $space -> StringPartValue
# "$space" -> StringPartValue
# $myarray -> ArrayPartValue
# $glob -> StringPartValue
#
# Then I _MakeWordFrames.  Each frame is (frag, list)

# (frag, do_split_elide)
# 
# [ ('-a b', False) ]
# [ ('c d', False), ('-', False), (' ', True), ('-', False), (' ', False),
#   ('-', False), ('w x', False) ]
# [ ('y z', False) ]
# [ ('bin', False), ('*h b*', True) ]


# Then for each frame, do _EvalWordFrame.  Respect the boolean, and do
# glob.GlobEscape or self.splitter.Escape(frag)

# '-a b'
# -> Glob escape
# '-a b'
# -> Split EScape
# '-a\ b'

# 'c\ d-'
# '-'

# Possible fix to IFS='\' problem: do globbing and splitting in two completely
# separate steps.  The Split() function should respect [(frag, bool do_split) ...]
#
# If not splitting, then it's easy to emit the span.


