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

control-flow() {
  banner 'BREAK'

  # this is a syntax error!  OK good
  nodejs -e '
  function f() {
    break;
  }
'
}

use-strict-static() {
  set +o errexit

  banner 'DUPE PARAMS'
  nodejs -e '
  "use strict";
  function f(a, a) {
    return 42;
  }
  '

  banner 'OCTAL'
  nodejs -e '
  "use strict";
  function f(a) {
    return 0123;
  }
  '

  banner 'WITH'

  nodejs -e '
  "use strict";
  function f() {
    with (x) {
      console.log(x);
    }
  }
  '

  banner 'OBJECT KEYS'

  # Claude AI hallucinated this duplicate object keys, and then corrected itself
  nodejs -e '
  "use strict";
  function f() {
    return {a:1, a:2};
  }
  '
}

branches() {
  set +o errexit

  # spec/ysh-user-feedback - Julian

  # JavaScript allows this because it's block scoped
  banner 'IF'
  nodejs -e '
  function f(x) {
    if (x === 2) {
      let tmp = "hello"
    } else {
      let tmp = "world"
      // This is an error
      // let tmp = "z"
    }
    //console.log(tmp);
  }

  f(1);
  f(2);
  '

  banner 'SWITCH'
  nodejs -e '
  function f(x) {
    switch (x) {
      case 1:
        let tmp = "hello"
        break;
      case 2:
        let tmp = "world"
        break;
    }
  }

  f(1);
  f(2);
  '

  banner 'SWITCH BLOCK'
  nodejs -e '
  function f(x) {
    switch (x) {
      case 1: {
        let tmp = "hello"
        console.log(tmp);
        break;
      }
      case 2: {
        let tmp = "world"
        console.log(tmp);
        break;
      }
    }
  }

  f(1);
  f(2);
  '
}

loop() {
  banner 'MODIFY FOR'
  nodejs -e '
  function f() {
    for (let x of [1, 2]) {
      console.log(`x = ${x}`);
      x = 3;
      console.log(x);
    }
  }

  f();
  '

  # Hm why is this allowed?
  banner 'LET LET'
  nodejs -e '
  function f() {
    for (let x of [1, 2]) {
      // console.log(`x = ${x}`);
      let x = 3;
      console.log(x);
    }
  }

  f();
  '
  # Claude AI claims that there are two nested scopes, but I'm not so sure
  # It seemed to enter an infinite loop where the code analysis didn't agree
  # with it

  # It also refers to "loop initialization scope" and "loop body scope"

  # Another attempt:

  # "What the specification actually describes is more precise and technical.
  # For a for...of loop like for (let x of [1,2]) { let x = 3 }, the ECMAScript
  # spec (as of ES2022) describes the behavior using concepts like:

  # "Per-iteration binding instantiation - Each iteration of the loop creates a
  # new lexical environment for the loop variable
  #
  # "Block scoping - The {} of the loop body creates its own lexical environment

  # "According to the specification, for loops with let declarations create a
  # fresh binding (variable) for each iteration of the loop. The loop body then
  # creates another lexical environment (scope) where another binding with the
  # same name can exist independently.

  # "The precise section in the ECMAScript spec that addresses this is
  # typically found in sections covering "for statement" execution semantics.
  # The loop iteration variable and the loop body variable are in different
  # lexical environments in the specification's terminology, rather than
  # different "scopes" as I informally described.

  banner 'LET x y'
  nodejs -e '

  // Uh this is weird too, y = 1?
  function f() {
    for (let x = 0, y = x + 1; x < 5; ++x) {
      console.log(`x = ${x}, y = ${y}`);
      //let x = 3;
    }
  }

  f();
  '
}


use-strict-dynamic() {
  set +o errexit

  banner 'STRICT UNDEF'
  nodejs -e '
  "use strict";

  function outer() {
    let y = x + 1;  // ReferenceError
    console.log(`x=${x}`);
  }

  outer();
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
}

"$@"
