#!/usr/bin/env bash
#
# Survey closures, with a bunch of comments/notes
#
# Usage:
#   demo/survey-closure.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # python3 in $PATH

counter() {
  echo 'COUNTER JS'
  echo

  nodejs -e '
  function createCounter() {
    let count = 0;
    return function() {
      // console.log("after", after);
      count++;
      return count;
    };
    let after = 42;
  }

  const counter = createCounter();
  console.assert(counter() === 1, "Test 1.1 failed");
  console.assert(counter() === 2, "Test 1.2 failed");

  console.log(counter());
  '

  echo 'COUNTER PYTHON'
  echo

  python3 -c '
def create_counter():
  count = 0
  def counter():
      # Python lets you do this!
      #print("after", after);
      nonlocal count
      count += 1
      return count
  after = 42
  return counter

counter = create_counter()
assert counter() == 1, "Test 1.1 failed"
assert counter() == 2, "Test 1.2 failed"

print(counter())
'
}

# The famous C# / Go issue, and the design note at the end:
#
# http://craftinginterpreters.com/closures.html
#
# "If a language has a higher-level iterator-based looping structure like
# foreach in C#, Java’s “enhanced for”, for-of in JavaScript, for-in in Dart,
# etc., then I think it’s natural to the reader to have each iteration create a
# new variable. The code looks like a new variable because the loop header
# looks like a variable declaration."
#
# I am Python-minded and I think of it as mutating the same location ...
#
# "If you dig around StackOverflow and other places, you find evidence that
# this is what users expect, because they are very surprised when they don’t
# get it."
#
# I think this depends on which languages they came from
# 
# JavaScript var vs. let is a good counterpoint ...
#
# Another solution for us is to make it explicit:
#
# captured var x = 1
#
# "The pragmatically useful answer is probably to do what JavaScript does with
# let in for loops. Make it look like mutation but actually create a new
# variable each time, because that’s what users want. It is kind of weird when
# you think about it, though."
#
# Ruby has TWO different behaviors, shown there:
#
# - for i in 1..2 - this is mutable
# - (1..2).each do |i| ... - this creates a new variable

loops() {
  echo 'LOOPS JS'
  echo

  nodejs -e '
  function createFunctions() {
    const funcs = [];
    for (let i = 0; i < 3; i++) {
      funcs.push(function() { return i; });
    }
    return funcs;
  }

  const functions = createFunctions();
  console.assert(functions[0]() === 0, "Test 4.1 failed");
  console.assert(functions[1]() === 1, "Test 4.2 failed");
  console.assert(functions[2]() === 2, "Test 4.3 failed");

  console.log(functions[2]())
  '

  echo 'LOOPS PYTHON'
  echo

  # We would have to test multiple blocks in a loop
  #
  # for i in (0 .. 3) {
  #   cd /tmp {  # this will work
  #     echo $i
  #   }
  # }

  python3 -c '
def create_functions():
    funcs = []
    for i in range(3):
        # TODO: This is bad!!!  Not idiomatic
        funcs.append(lambda i=i: i)  # Using default argument to capture loop variable
        #funcs.append(lambda: i)
    return funcs

functions = create_functions()

for i in range(3):
  actual = functions[i]()
  assert i == actual, "%d != %d" % (i, actual)

print(functions[2]())
    '
}

js-while-var() {
  echo 'WHILE JS'
  echo

  nodejs -e '
  function createFunctions() {
    const funcs = [];
    let i = 0;  // for let is SPECIAL!
    while (i < 3) {
      funcs.push(function() { return i; });
      i++;
    }
    return funcs;
  }

  const functions = createFunctions();

  console.log(functions[0]())
  console.log(functions[1]())
  console.log(functions[2]())
  '

  echo 'FOR VAR JS'
  echo

  nodejs -e '
  function createFunctions() {
    const funcs = [];
    // var is not captured
    for (var i = 0; i < 3; i++) {
      funcs.push(function() { return i; });
    }
    return funcs;
  }

  const functions = createFunctions();

  console.log(functions[0]())
  console.log(functions[1]())
  console.log(functions[2]())
  '

  echo 'FOR LET'
  echo

  nodejs -e '
  function createFunctions() {
    const funcs = [];
    for (let i = 0; i < 3; i++) {
      // This is captured
      // let j = i + 10;

      // This is not captured, I guess it is "hoisted"
      var j = i + 10;
      funcs.push(function() { return j; });
    }
    return funcs;
  }

  const functions = createFunctions();

  console.log(functions[0]())
  console.log(functions[1]())
  console.log(functions[2]())
  '
}

nested() {
  echo 'NESTED JS'
  echo

  nodejs -e '
  function outer(x) {
    return function(y) {
      return function(z) {
        return x + y + z;
      };
    };
  }
  '

  echo 'NESTED PYTHON'
  echo

  python3 -c '
def outer(x):
    def middle(y):
        def inner(z):
            return x + y + z
        return inner
    return middle

nested = outer(1)(2)
assert nested(3) == 6, "Test 2 failed"
    '
}

value-or-var() {
  # Good point from HN thread, this doesn't work
  #
  # https://news.ycombinator.com/item?id=21095662
  #
  # "I think if I were writing a language from scratch, and it included
  # lambdas, they'd close over values, not variables, and mutating the
  # closed-over variables would have no effect on the world outside the closure
  # (or perhaps be disallowed entirely)."
  #
  # I think having 'capture' be syntax sugar for value.Obj could do this:
  #
  # func f(y) {
  #   var z = {}
  #
  #   func g(self, x) capture {y, z} -> Int {
  #     return (self.y + x)
  #   }
  #   return (g)
  # }
  #
  # Now you have {y: y, z: z} ==> {__call__: <Func>}
  #
  # This would be syntax sugar for:
  #
  # func f(y) {
  #   var z = {}
  #
  #   var attrs = {y, z}
  #   func g(self, x) -> Int {
  #     return (self.y + x)
  #   }
  #   var methods = Object(null, {__call__: g}
  #
  #   var callable = Object(methods, attrs))
  #   return (callable)
  # }
  #
  # "This mechanism that you suggest about copying values is how Lua used to
  # work before version 5.0, when they came up with the current upvalue
  # mechanism"
  #
  # I think we could use value.Place if you really want a counter ... 
  #
  # call counter->setValue(counter.getValue() + 1)

  echo 'VALUE JS'
  echo

  nodejs -e '
  var x = 42;
  var f = function () { return x; }
  x = 43;
  var g = function () { return x; }

  console.log(f());
  console.log(g());
  '

  # Hm doesn't work
  echo

  nodejs -e '
  let x = 42;
  let f = function () { return x; }
  x = 43;
  let g = function () { return x; }

  console.log(f());
  console.log(g());
  '

  echo
  echo 'VALUE PYTHON'
  echo

  python3 -c '
x = 42
f = lambda: x
x = 43
g = lambda: x

print(f());
print(g());
'

  echo
  echo 'VALUE LUA'
  echo

  lua -e '
local x = 42
local f = function() return x end
x = 43
local g = function() return x end

print(f())
print(g())
'
}

# More against closures:
#
# https://news.ycombinator.com/item?id=22110772
#
# "I don't understand the intuition of closures and they turn me off to
# languages immediately. They feel like a hack from someone who didn't want to
# store a copy of a parent-scope variable within a function."
#
# My question, against local scopes (var vs let in ES6) and closures vs.
# classes:
#
# https://news.ycombinator.com/item?id=15225193
#
# 1. Modifying collections. map(), filter(), etc. are so much clearer and more
# declarative than imperatively transforming a collection.

# 2. Callbacks for event handlers or the command pattern. (If you're using a
# framework that isn't event based, this may not come up much.)

# 3. Wrapping up a bundle of code so that you can defer it, conditionally,
# execute it, execute it in a certain context, or do stuff before and after it.
# Python's context stuff handles much of this for you, but then that's another
# language feature you have to explicitly add.

# Minority opinion about closures:
#
# - C# changed closure-in-loop
# - Go changed closure-in-loop
# - Lua changed as of 5.0?
#   - TODO: Test out closures in Lua too
#
# - Python didn't change it, but people mostly write blog posts about it, and
# don't hit it?

"$@"
