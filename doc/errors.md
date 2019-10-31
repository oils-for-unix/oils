---
in_progress: yes
---

List of Errors in the OSH Interpreter
=====================================

<div id="toc">
</div>

Parse Error:
  Can be determined statically
  spec/parse-errors.test.sh



TODO: See test/runtime-errors.sh.  Merge them here.

## Fatal vs. Non-Fatal

Fatal Error:
  terminates the interpreter unconditionally, e.g. divide by zero does this in
  bash.

Non-fatal error:
  terminates the current builtin and exits 1

non-fatal errors can be turned into fatal errors.

by Strict modes:
    set -o errexit

strict modes can also things that are not errors at all into fatal errors
    set -o nounset
    set -o failglob

Fatal errors can be turned into non-fatal ones!!!!

by dparen:

   (( 1 / 0 ))

by command sub -- although this involves another process so it's
understandable!

   set -o errexit
   echo $(exit 1)

## Strict Modes

strict_array
strict_errexit
strict_arith

TODO: strict-word-eval?
  for unicode errors
  for subshell negative indices?  I think this is most consistent right now.


## Parse Error API

TODO:

    p_die() internally


    w = w_parser.ReadWord()
    if w is None:
      do something with w_parser.Error()

Related to memory management API:

    # arena is the out param
    arena = pool.NewArena()
    c_parser = cmd_parse.CommandParser(w_parser, arena)
    bool ok = c_parser.Parse()
    if ok:
      arena.RootNode() #  turns indexes into pointers?
      arena.Deallocate()  # d
    else:
      c_parser.Error()  # Is this still a stack?

## Runtime Error API: error codes + error contexts?

Idea:

- Should we have a table of errors for metaprogramming?
  - assign each one of these a code, and decide what to do based on a table?
  - then have an error CONTEXT
  - based on spec tests?

  - and error context takes an error code, looks it up in a table, and decides
    whether to catch or to reraise!

List of contexts:

- assignment   a=$()    exit code
- command sub $()
- subshell ()
- pipeline?  ls | { foo; exit 1; }
- dparen (( )) vs. arith sub $(( ))

## Problem in bash: Context affects a lot

echo $(( 1 / 0 ))
echo 'after-$(())
(( 1 / 0 ))
echo 'after-$(())


## Arith Eval

Divide by zero: $(( 1 / 0 ))

                      ^
Maybe: integer overflow.  But we want big numbers.

Type errors between integers and strings:

    x=foo
    $(( x * 2 ))  # doesn't make sense, except in bash's crazy world.

Invalid hex constant:

    x=0xabcg
    echo $(( x * 2 ))   (fatal in bash)

## Bool Eval

regcomp parse error: 

x=$(cat invalid-syntax.txt)
[[ foo =~ $x ]]

## Word Eval

IMPORTANT: Command sub error $(exit 1)

User-requested error:  ${undef?error}

set -o nounset

    def _EmptyStrOrError(self, val, token=None):
      # calls `e_die()`

Variants:
  nounset: index out of bounds ${a[3]}
  I guess same diagnostic?

In bash you can set an index out of bounds, like
b[2]=9  
Might want to have a mode for this?

set -o failglob
     TODO: not implemented
     might need PWD diagnostic
     


Redirects:
  Redirect to empty filename/descriptor ( or array)

{ break; }   
  ^~~~~~ break only invalid inside loop, etc.


NotImplementedError
  - e.g for var ref ${!a}
  - bash associative arrays?  I think we want most of that
  - $"" ?
  - |& not yet done
  - ;;& for case -- although parsing it is all of the work I guess
  - some could be parse time errors too though?


- String Slicing and String Length require valid utf-8 characters

    s=$(cat invalid.txt)
    echo ${#s}  # code points
    echo ${s:1:3}  # code opints

- Slicing: Index is negative.  ${foo: -4} and ${foo: 1 : -4} aren't supported
  right now, unlike bash and zsh.

## Command Exec

IMPORTANT: subshell error ( exit 1 )

set -o errexit  -- turns NON-FATAL error into FATAL error.

set -o pipefail
  pipefail might need some fanciness for ${PIPESTATUS}

Trying to set readonly variable:
  readonly foo=bar
  foo=x
  (could any of this be done at compile time?)

  - this needs two locations: where the assignment was, and where it was
    declared readonly.

Trying to redeclare a variable?  That can also be parse time.
local x=1
local x=2

Type errors between Str and StrArray:  -- strict-array controls this
    EvalWordToString calls e_die()`

  echo foo > "$@"
             ^--    # Should have what it evaluated to?  # This could be static too

  case "$@" in
    "$@") echo bad;;
  esac

  ${undef:-"$@"} is OK, but ${var%"$@"}  doesn't make sense really.
  ${v/"$@"/"$@"}


LHS evaluation:
  s='abc'
  s[1]=X  # invalid because it's a string, not an array


Invalid descriptor:


fd=$(cat invalid.txt)
echo foo 2>& $fd

### Builtins

In core/builtins.py:

    util.usage('...')
    return 1

A usage error is a runtime error that results in the builtin returning 1.

Builtin has too many arguments -- but this falls under the errexit rule
  cd foo bar baz
  continue "$@"
(Parse error: continue 1 2 3)

Although we might want to highlight the extra args.



## Syscall Failures

Fatal error from system calls:
    fork() could fail in theory

Some are not failures:

    stat() [[ -f /tmp/foo ]] 
    cd /ff  chdir()  # exit code 1
    cat <nonexistent  # This is just exit code 1 

## Interpreter Failures

Runtime: Stack Too Deep (catch infinite recursion)
Out of memory: should not happen with OSH, but maybe with Oil

Runtime Parse Errors
--------------------

The way bash works 0x$var can be a hex literal.
so var=xx makes this invalid.   hex/octal/decimal have this problem.


Parse Time Errors
-----------------

regcomp() errors (sometimes at parse time; other times at runtime)

Need to show stack trace for "source" like Python.  Prototype this.

Also might show which token thing caused you to be in arith parse state, like:

$((echo hi))
^~      ^~
Arith   Invalid token


