---
in_progress: yes
---

Syntactic Concepts in Oil
=========================

Shell has these concepts.

Sigils:

    echo $var
    echo "$@"

Sigil Pairs:

    echo ${var} 
    echo $(hostname)  #
    echo $((1 + 2 ))

Oil extends them.

<div id="toc">
</div> 

## Static Parsing

Like Python, JS.  See Oil language definition.

- [[ ]] and []
- echo -e and $''

- remaining dynamic parsing in shell
  - printf
  - glob
- arithmetic is still somewhat dynamic -- replaced by Oil expressions
- assignment builtins support dynamism, replaced by `var` and `setvar`

## Parsing Options to Take Over @, (), {}, `set`, and maybe =

Another concept is parsing modes.


    shopt -s all:oil  # most important thing, turns on many options

    if ( ) {
    }

    echo @array

    set x = 1
    builtin set -o errexit

equals:

    x = 1
    equivalent to 
    const x = 1

This is for Oil as a **configuration language**.

## Command vs. Expression Mode

See [Command vs. Expression Mode](command-vs-expression-mode.html).

    echo hi

Expression mode in three places:

    echo @array
    myprog --flag=$f(x, y)
    var z = f(x+1, y)

Control FLow:

   if grep foo
   if (foo) {}   # replaces if [ -n $foo ]; then

   while

   for

   switch/case -- for translation to C++ like mycpp
   match/case


## Sigils, Sigil Pairs, and Lexer Modes

Sigils:

- $foo for string
- @array for array of strings
- : sort of means "code" ?

Sigil Pairs:

- ${x} for word evaluation
- $(( )) for shell arithmetic is deprecated

- $(bare words) for command sub
- %(bare words) for shell arrays
- %[1 2 3] for typed arrays
- %{ } for table literals / embedded TSV

- $// for regexes

- c'' c"" r'' r"" for strings
  - legacy: $'' in command mode

- :{} for blocks
- :() for unevaluated expressions

Table example:

    var people = %{
      name      age:Int
      bob       10_000
      'andy c'  15_000
    }
    var people = {name: %(bob 'andy c'), age: %[10_000 15_000]}


- maybe: #() for tuple?

Sigil pairs often change the lexer mode.

