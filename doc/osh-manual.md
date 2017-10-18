OSH Reference Manual
--------------------

## set builtin

### errexit

It largely follows the logic of bash.  Any non-zero exit code causes a fatal
error, except in:
 
  - the condition part of if / while / until
  - a command/pipeline prefixed by !
  - Every clause in || and && except the last

However, we fix two bugs with bash's behavior:

  - failure in $() should be fatal, not ignored.  OSH behaves like dash and
    mksh, not bash.
  - failure in local foo=... should propagate.  
    OSH diverges because this is arguably a bug in all shells -- `local` is
    treated as a separate command, which means `local foo=bar` behaves
    differently than than `foo=bar`.

Here is another difference:

  - If 'set -o errexit' is active, and then we disable it (inside
    if/while/until condition, !, && ||), and the user tries to 'set +o
    errexit', back, then this is a fatal error.  Other shells delay setting
    back until after the whole construct.

Very good articles on bash errexit:

  - http://mywiki.wooledge.org/BashFAQ/105
  - http://fvue.nl/wiki/Bash:_Error_handling

## Notable Gotchas in Parsing

Arith Sub vs. Command Sub:

- Unlike bash, `$((` is always starts an arith sub.  `$( (echo hi) )` is a
  subshell inside a command sub.  (This construct should be written
  `({ echo hi;})` anyway.

Extended Glob vs. Negation of Expression:

- `[[ !(a == a) ]]` is always an extended glob.  
- `[[ ! (a == a) ]]` is the negation of an equality test.
  - In bash the rules are much more complicated, and depend on `shopt -s
    extglob`.  That flag is a no-op in OSH.  OSH avoids dynamic parsing, while
    bash does it in many places.

## Unicode

Encoding of programs should be utf-8.

But those programs can manipulate data in ANY encoding?

    echo $'[\u03bc]'  # C-escaped string

vs literal unicode vs. `echo -e`.  `$''` is preferred because it's statically
parsed.


List of operations that are Unicode-aware:

- ${#s} -- number of characters in a string
- slice: ${s:0:1}
- any operations that uses glob, which has '.' and [[:alpha:]] expressions
  - case
  - [[ $x == . ]]
  - ${s/./x}
  - ${s#.}  # remove one character
- sorting [[ $a < $b ]] -- should use current locale?  I guess that is like the
  'sort' command.
- prompt string has time, which is locale-specific.


