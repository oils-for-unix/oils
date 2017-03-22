List of Fatal Runtime Errors
----------------------------
 
User-requested error:  ${undef?error}

set -o nounset
set -o errexit
set -o pipefail
  pipefail might need some fanciness for ${PIPESTATUS}
set -o failglob
  failglob: might need PWD diagnostic

Variants:
  nounset: index out of bounds
  I guess same diagnostic?

In bash you can set an index out of bounds, like
b[2]=9  
Might want to have a mode for this?



Trying to set readonly variable:
  readonly foo=bar
  foo=x
  (could any of this be done at compile time?)

  - this needs two locations: where the assignment was, and where it was
    declared readonly.

Trying to redeclare a variable?  That can also be parse time.
local x=1
local x=2


Divide by zero: $(( 1 / 0 ))
                      ^
Maybe: integer overflow.  But we want big numbers.

Type errors between Str and StrArray:

  echo foo > "$@"
             ^--    # Should have what it evaluated to?
                    # This could be static too

  case "$@" in
    "$@") echo bad;;
  esac

  ${undef:-"$@"} is OK, but ${var%"$@"}  doesn't make sense really.
  ${v/"$@"/"$@"}

Type errors between integers and strings:

  x = foo
  $(( x * 2 ))  # doesn't make sense, except in bash's crazy world.


Builtin has too many arguments -- but this falls under the errexit rule
  cd foo bar baz
  continue "$@"
(Parse error: continue 1 2 3)

Although we might want to highlight the extra args.


Error from stat() system call:

[[ -f /tmp/foo ]] 

Redirects:
  Redirect to empty filename/descriptor ( or array)

{ break; }   
  ^~~~~~ break only invalid inside loop, etc.


Runtime: Stack Too Deep (catch infinite recursion)
Out of memory: should not happen with OSH, but maybe with Oil

Runtime Parse Errors
--------------------

The way bash works 0x$var can be a hex literal.
so var=xx makes this invalid.   hex/octal/decimal have this problem.

