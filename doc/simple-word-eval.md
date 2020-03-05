Simple Word Evaluation in Unix Shell
====================================

<!-- override web/language.css because there's too much bold -->
<style>
.sh-command {
  font-weight: normal;
}
</style>

This document describes Oil's word evaluation semantics (`shopt -s
simple_word_eval`) for experienced shell users.  It may also be useful to
those who want to implement this behavior in another shell.

The main idea is that Oil behaves like a traditional programming language:

1. It's **parsed** from start to end [in a single pass][parsing-shell].
2. It's **evaluated** in a single step too.

That is, parsing and evaluation aren't interleaved, and code and data aren't
confused.

[parsing-shell]: https://www.oilshell.org/blog/2019/02/07.html

[posix-spec]: https://pubs.opengroup.org/onlinepubs/009695399/utilities/xcu_chap02.html#tag_02_06


<div id="toc">
</div>

## An Analogy: Word Expressions Should Be Like Arithmetic Expressions

In Oil, "word expressions" like

    $x
    "hello $name"
    $(hostname)
    'abc'$x${y:-${z//pat/replace}}"$(echo hi)$((a[i] * 3))"
    
are parsed and evaluated in a straightforward way, like this expression when `x
== 2`:

```sh-prompt
1 + x / 2 + x * 3        → 8  # Python, JS, Ruby, etc. work this way
```

In contrast, in shell, words are "expanded" in multiple stages, like this:

```sh-prompt
1 + "x / 2 + \"x * 3\""  → 8  # Hypothetical, confusing language
```

That is, it would be odd if Python looked *inside a program's strings* for
expressions to evaluate, but that's exactly what shell does!  There are
multiple places where there's a silent `eval`, and you need **quoting** to
inhibit it.  Neglecting this can cause security problems due to confusing code
and data (links below).

In other words, the **defaults are wrong**.  Programmers are surprised by shell's
behavior, and it leads to incorrect programs.

So in Oil, you can opt out of the multiple "word expansion" stages described in
the [POSIX shell spec][posix-spec].  Instead, there's only **one stage**:
evaluation.

## Design Goals

The new semantics should be easily adoptable by existing shell scripts.

- Importantly, `bin/osh` is POSIX-compatible and runs real [bash]($xref)
  scripts.  You can gradually opt into **stricter and saner** behavior with
  `shopt` options (or by running `bin/oil`).  The most important one is
  [simple_word_eval]($help), and the others are listed below.
- Even after opting in, the new syntax shouldn't break many scripts.  If it
  does break, the change to fix it should be small.  For example, `echo @foo`
  is not too common, and it can be made bash-compatible by quoting it: `echo
  '@foo'`.

<!--
It's technically incompatible but I think it will break very few scripts.

-->

## Examples

In the following examples, the [argv][] command prints the `argv` array it
receives in a readable format:

```sh-prompt
$ argv one "two three"
['one', 'two three']
```

I also use Oil's [var]($help) keyword for assignments.  *(TODO: This could be
rewritten with shell assignment for the benefit of shell implementers)*

[argv]: $oil-src:spec/bin/argv.py

### No Implicit Splitting, Dynamic Globbing, or Empty Elision

In Oil, the following constructs always evaluate to **one argument**:

- Variable / "parameter" substitution: `$x`, `${y}`
- Command sub: `$(echo hi)` or backticks
- Arithmetic sub: `$(( 1 + 2 ))`


<!--
Related help topics: [com-sub]($help), [var-sub]($help), [arith-sub]($help).
Not shown: [tilde-sub]($help).
-->

That is, quotes aren't necessary to avoid:

- **Word Splitting**, which uses `$IFS`.
- **Empty Elision**.  For example, `x=''; ls $x` passes `ls` no arguments.
- **Dynamic Globbing**.  Globs are *dynamic* when the pattern comes from
  program data rather than the source code.

<!-- - Tilde Sub: `~bob/src` -->

Here's an example showing that each construct evaluates to one arg in Oil:

```sh-prompt
oil$ var pic = 'my pic.jpg'  # filename with spaces
oil$ var empty = ''
oil$ var pat = '*.py'        # pattern stored in a string

oil$ argv ${pic} $empty $pat $(cat foo.txt) $((1 + 2))
['my pic.jpg', '', '*.py', 'contents of foo.txt', '3']
```

In contrast, shell applies splitting, globbing, and empty elision after the
substitutions.  Each of these operations returns an indeterminate number of
strings:

```sh-prompt
sh$ pic='my pic.jpg'  # filename with spaces
sh$ empty=
sh$ pat='*.py'        # pattern stored in a string

sh$ argv ${pic} $empty $pat $(cat foo.txt) $((1 + 2))
['my', 'pic.jpg', 'a.py', 'b.py', 'contents', 'of', 'foo.txt', '3']
```

To get the desired behavior, you have to use double quotes:

```sh-prompt
sh$ argv "${pic}" "$empty" "$pat", "$(cat foo.txt)" "$((1 + 2))"
['my pic.jpg', '', '*.py', 'contents of foo.txt', '3']
```

### Splicing, Static Globbing, and Brace Expansion

The constructs in the last section evaluate to a **single argument**.  In
contrast, these three constructs evaluate to **0 to N arguments**:

1. **Splicing** an array: `"$@"` and `"${myarray[@]}"`
2. **Static Globbing**: `echo *.py`.  Globs are *static* when they occur in the
   program text.
3. **Brace expansion**: `{alice,bob}@example.com`

In Oil, `shopt -s parse_at` enables these shortcuts for splicing:

- `@myarray` for `"${myarray[@]}"`
- `@ARGV` for `"$@"`

Example:

```sh-prompt
oil$ var myarray = @('a b' c)  # array with 2 elements
oil$ set -- 'd e' f            # 2 arguments

oil$ argv @myarray @ARGV *.py {ian,jack}@sh.com
['a b', 'c', 'd e', 'f', 'g.py', 'h.py', 'ian@sh.com', 'jack@sh.com']
```

is just like:


```sh-prompt
bash$ myarray=('a b' c)
bash$ set -- 'd e' f

bash$ argv "${myarray[@]}" "$@" *.py {ian,jack}@sh.com
['a b', 'c', 'd e', 'f', 'g.py', 'h.py', 'ian@sh.com', 'jack@sh.com']
```

Unchanged: quotes disable globbing and brace expansion:

```sh-prompt
$ echo *.py
foo.py bar.py

$ echo "*.py"            # globbing disabled with quotes
*.py

$ echo {spam,eggs}.sh
spam.sh eggs.sh

$ echo "{spam,eggs}.sh"  # brace expansion disabled with quotes
{spam,eggs}.sh
```

<!--
Key differences is **quoting** and the `@` **splice** operator.

The "arity" of the command is more static than dynamic, because there's no
splitting.  Splitting can be done with `@split(mystr)` and dynamic globbing
could be `@glob(myglobstr)` (not implemented)
-->

<!--
help topics:

- braces
- glob
- splice

More:
- inline-call

-->

## Where These Rules Apply

These rules apply when a **sequence** of words is being evaluated, exactly as
in shell:

1. [Command]($help:simple-command): `echo $x foo`
2. [For loop]($help:for): `for i in $x foo; do ...`
3. [Array Literals]($help:array): `a=($x foo)` and `var a = @($x foo)` ([oil-array]($help))

Shell has other word evaluation contexts like:

```sh-prompt
sh$ x="${not_array[@]}"
sh$ echo hi > "${not_array[@]}"
```

which aren't affected by [simple_word_eval]($help).

<!--
EvalWordSequence
-->

## Opt In to the Old Behavior With Explicit Expressions

Oil can express everything that shell can.

- Split with `@split(mystr, IFS?)`
- Glob with `@glob(mypat)`
- Elision with `@maybe(s)`

## More Word Evaluation Issues

### More `shopt` Options

- [nullglob]($help) - Globs matching nothing don't evaluate to code.
- [dashglob]($help) is true by default, but **disabled** when Oil is enabled, so that
  files that begin with `-` aren't returned.  This avoids [confusing flags and
  files](https://www.oilshell.org/blog/2020/02/dashglob.html).

Strict options cause fatal errors:

- [strict_tilde]($help) - Failed tilde expansions don't evaluate to code.
- [strict_word_eval]($help) - Invalid slices and invalid UTF-8 aren't ignored.

### Arithmetic Is Statically Parsed

This is an intentional incompatibility described in the [Known
Differences](known-differences.html#static-parsing) doc.

<!--
TODO: also allow

var parts = @split(x) 
var python = @glob('*.py')
-->

## Summary

Oil word evaluation is enabled with `shopt -s simple_word_eval`, and proceeds
in a single step.

Variable, command, and arithmetic substitutions predictably evaluate to a
**single argument**, regardless of whether they're empty or have spaces.
There's no implicit splitting, globbing, or elision of empty words.

You can opt into those behaviors with explicit expressions like
`@split(mystr)`, which evaluates to an array.

Oil also supports shell features that evaluate to **0 to N arguments**:
splicing, globbing, and brace expansion.

There are other options that "clean up" word evaluation.  All options are
designed to be gradually adopted by other shells, shell scripts, and eventually
POSIX.

## Notes

### Related Documents

- [The Simplest Explanation of
  Oil](http://www.oilshell.org/blog/2020/01/simplest-explanation.html).  Some
  color on the rest of the language.
- [Known Differences Between OSH and Other Shells](known-differences.html).
  Mentioned above: Arithmetic is statically parsed.  Arrays and strings are
  kept separate.
- [OSH Word Evaluation Algorithm][wiki-word-eval] on the Wiki.  Informally
  describes the data structures, and describes legacy constructs.
- [Security implications of forgetting to quote a variable in bash/POSIX
  shells](https://unix.stackexchange.com/questions/171346/security-implications-of-forgetting-to-quote-a-variable-in-bash-posix-shells)
  by Stéphane Chazelas.  Describes the "implicit split+glob" operator, which
  Oil word evaluation removes.
  - This is essentially the same [security
    issue](http://www.oilshell.org/blog/2019/01/18.html#a-story-about-a-30-year-old-security-problem)
    I rediscovered in January 2019.  It appears in all [ksh]($xref)-derived shells, and some shells
    recently patched it.  I wasn't able to exploit in a "real" context;
    otherwise I'd have made more noise about it.
  - Also described by the Fedora Security team: [Defensive Coding: Shell Double Expansion](https://docs.fedoraproject.org/en-US/Fedora_Security_Team/1/html/Defensive_Coding/sect-Defensive_Coding-Shell-Double_Expansion.html)

[wiki-word-eval]: https://github.com/oilshell/oil/wiki/OSH-Word-Evaluation-Algorithm

### Tip: View the Syntax Tree With `-n`

This gives insight into [how Oil parses shell][parsing-shell]:

```sh-prompt
$ osh -n -c 'echo ${x:-default}$(( 1 + 2 ))'
(C {<echo>} 
  {
    (braced_var_sub
      token: <Id.VSub_Name x>
      suffix_op: (suffix_op.Unary op_id:Id.VTest_ColonHyphen arg_word:{<default>})
    ) 
    (word_part.ArithSub
      anode: 
        (arith_expr.Binary
          op_id: Id.Arith_Plus
          left: (arith_expr.ArithWord w:{<Id.Lit_Digits 1>})
          right: (arith_expr.ArithWord w:{<Id.Lit_Digits 2>})
        )
    )
  }
)
```

You can pass `--ast-format text` for more details.

Evaluation of the syntax tree is a single step.


<!--

### Elision Without @maybe()

The `@maybe(s)` function is a shortcut for something like:

```
var x = ''         # empty in this case
var tmp = @()
if (x) {           # test if string is non-empty
  append :tmp $x   # appends 'x' to the array variable 'tmp'
}
```

This is how it's used:

-->
