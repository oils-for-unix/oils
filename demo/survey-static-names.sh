#!/usr/bin/env bash
#
# Survey static name analysis with JS let const
#
# Usage:
#   demo/survey-static-names.sh <function name>
#
# Static checks - SyntaxError
#   let const
#
# Dynamic checks - SyntaxError
#
# YSH TODO:
# - var setvar check should be dynamic, not static
#   - e.g. setvar assumes the cell already exists
# - var var check - not sure if this can be done statically
#   - depends on block scope, and blocks can be evalInFrame()
# - const within functions
#   - can we bring this back?
#   - it is OK within loops, now that we have
#
# - And I think
#   x = 'const'         # always available?  For syntax highlighting
#   const x = 'const'   # this is the synonym
#
# But we prefer 
# - "bare" style in Attr blocks
# - explicit const everywhere else

set -o nounset
set -o pipefail
set -o errexit

banner() {
  echo
  echo "*** $@ ***"
  echo
}

js-var() {
  set +o errexit

  banner 'LET LET'
  nodejs -e '
  function outer() {
    let x = "X_outer";
    let x = "Y_outer";
  }
  '

  banner 'LET CONST'
  nodejs -e '
  function outer() {
    let x = "X_outer";
    const x = "Y_outer";
  }
  '

  banner 'OK - LET CONST in inner scope'
  nodejs -e '
  function outer() {
    let x = "X_outer";
    if (true) {
      const x = "Y_outer";
    }
  }
  '

  banner 'LET VAR - disallowed'
  nodejs -e '
  function outer() {
    var x = "Y_outer";
    let x = "X_outer";
  }
  '

  banner 'CONST MUTATE'
  nodejs -e '
  function outer() {
    const x = "Y_outer";

    # Oh this is a dynamic check?  Does not fail
    x = "mutate"
  }
  '

  banner 'STRICT UNDEF'
  nodejs -e '
  "use strict";

  function outer() {
    let y = x + 1
    console.log(`x=${x}`);
  }
  '

  banner 'STRICT MUTATE'
  nodejs -e '

  // Use strict prevents global mutation!  But only at runtime
  "use strict";

  function outer() {
    x = "mutate"
  }

  outer();
  console.log(`was global created? x=${x}`);
  '

  banner 'USE BEFORE LET'
  nodejs -e '
  function outer() {
    // fails dynamically with ReferenceError
    console.log(`use before let: x=${x}`);
    let x = "foo";
  }

  outer();
  '

  echo
}

"$@"
