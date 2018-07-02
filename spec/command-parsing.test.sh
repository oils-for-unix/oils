#!/usr/bin/env bash
#
# Some nonsensical combinations which can all be detected at PARSE TIME.
# All shells allow these, but right now OSH disallowed.
# TODO: Run the parser on your whole corpus, and then if there are no errors,
# you should make OSH the OK behavior, and others are OK.

#### Prefix env on assignment
f() {
  # NOTE: local treated like a special builtin!
  E=env local v=var
  echo $E $v
}
f
## status: 0
## stdout: env var
## OK bash stdout: var
## OK osh status: 2
## OK osh stdout-json: ""

#### Redirect on assignment
f() {
  # NOTE: local treated like a special builtin!
  local E=env > _tmp/r.txt
}
rm -f _tmp/r.txt
f
test -f _tmp/r.txt && echo REDIRECTED
## status: 0
## stdout: REDIRECTED
## OK osh status: 2
## OK osh stdout-json: ""

#### Prefix env on control flow
for x in a b c; do
  echo $x
  E=env break
done
## status: 0
## stdout: a
## OK osh status: 2
## OK osh stdout-json: ""

#### Redirect on control flow
rm -f _tmp/r.txt
for x in a b c; do
  break > _tmp/r.txt
done
test -f _tmp/r.txt && echo REDIRECTED
## status: 0
## stdout: REDIRECTED
## OK osh status: 2
## OK osh stdout-json: ""
