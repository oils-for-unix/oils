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
