List of Errors in the OSH Interpreter
-------------------------------------

Parse Error:
  Can be determined statically
  spec/parse-errors.test.sh


TODO: See test/runtime-errors.sh.  Merge them here.

Fatal Error:
  terminates the interpreter unconditionally, e.g. divide by zero does this in
  bash.

Non-fatal error:
  terminates the current builtin and exits 1

Strict modes:
  Turns non-fatal errors into fatal errors.
    set -o errexit
  Turns things that are not errors at all into fatal errors
    set -o nounset
    set -o failglob


- Should we have a table of errors for metaprogramming?
  - assign each one of these a code, and decide what to do based on a table?
  - based on spec tests?

### Problem in bash: Context affects a lot

echo $(( 1 / 0 ))
echo 'after-$(())
(( 1 / 0 ))
echo 'after-$(())


### Arith Eval

Divide by zero: $(( 1 / 0 ))

                      ^
Maybe: integer overflow.  But we want big numbers.

Type errors between integers and strings:

    x=foo
    $(( x * 2 ))  # doesn't make sense, except in bash's crazy world.

Invalid hex constant:

    x=0xabcg
    echo $(( x * 2 ))   (fatal in bash)

### Bool Eval

regcomp parse error: 

x=$(cat invalid-syntax.txt)
[[ foo =~ $x ]]

### Word Eval

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

### Command Exec

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

#### Builtins

Builtin has too many arguments -- but this falls under the errexit rule
  cd foo bar baz
  continue "$@"
(Parse error: continue 1 2 3)

Although we might want to highlight the extra args.



### Syscall Failures

Fatal error from system calls:
    fork() could fail in theory

Some are not failures:

    stat() [[ -f /tmp/foo ]] 
    cd /ff  chdir()  # exit code 1
    cat <nonexistent  # This is just exit code 1 

### Interpreter Failures

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


