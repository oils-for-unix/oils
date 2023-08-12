---
default_highlighter: oil-sh
---

Syntactic Concepts in the Oil Language
======================================

These documents introduce the Oil language:

- [The Simplest Explanation of Oil ](//www.oilshell.org/blog/2020/01/simplest-explanation.html) (blog)
- [A Feel For Oil's Syntax](syntax-feelings.html)

In contrast, the concepts introduced below may help advanced users **remember**
Oil and its syntax.  Read on to learn about:

- **Command vs. Expression Mode**.  Command mode is like shell, and expression
  mode is like Python.
- **Lexer Modes** help parse different "sublanguages" or dialects.
- **Sigils and Sigil Pairs**.  A style of syntax that's familiar to shell and
  Perl users.
- **Parse Options** like `shopt -s parse_paren`.  To selectively break
  compatibility, and gradually upgrade shell to Oil.
- **Static Parsing**, as opposed to the dynamic parsing of shell.  Static
  parsing improves error messages and makes more software engineering tools
  possible.

<!-- TODO: We should talk about word lists: commands, array literals, and for
loops -->

<div id="toc">
</div> 

## Command vs. Expression Mode

The Oil parser starts out in command mode:

    echo "hello $name"

    for i in 1 2 3 {
      echo $i
    }

But it switches to expression mode in a few places:

    var x = 42 + a[i]          # the RHS of = is a YSH expression

    echo $[mydict['key']]      # interpolated expressions with $[]

    json write ({key: "val"})  # typed args inside ()

See [Command vs. Expression Mode](command-vs-expression-mode.html) for details.

## Lexer Modes

*Lexer modes* are a technique that Oil uses to manage the complex syntax of
shell, which evolved over many decades.

For example, `:` means something different in each of these lines:

    PATH=/bin:/usr/bin          # Literal string
    echo ${x:-default}          # Part of an operator
    echo $(( x > y ? 42 : 0 ))  # Arithmetic Operator
    var myslice = a[3:5]        # Oil expression

To solve this problem, Oil has a lexer that can run in many **modes**.
Multiple parsers read from this single lexer, but they demand different tokens,
depending on the parsing context.

### More Information

- [How OSH Uses Lexer Modes](//www.oilshell.org/blog/2016/10/19.html)
- [When Are Lexer Modes Useful?](//www.oilshell.org/blog/2017/12/17.html)
- [How to Parse Shell Like a Programming Language](//www.oilshell.org/blog/2019/02/07.html)
  - See the list of 14 lexer modes.
- [Posts tagged #lexing]($blog-tag:lexing)

## Sigils and Sigil Pairs

A **sigil** is a symbol like the `$` in `$mystr`.

A **sigil pair** is a sigil with opening and closing delimiters, like `${var}`
and `@(seq 3)`.

An appendix of [A Feel For Oil's Syntax](syntax-feelings.html) lists the sigil
pairs in the Oil language.

### Valid Contexts

Each sigil pair may be available in command mode, expression mode, or both.

For example, command substitution is available in both:

    echo $(hostname)      # command mode
    var x = $(hostname)   # expression mode

So are raw and C-style string literals:

    echo $'foo\n'  # the bash-compatible way to do it
    var s = $'foo\n'

    echo r'c:\Program Files\'
    var raw = r'c:\Program Files\'

But array literals only make sense in expression mode:

    var myarray = :| one two three |

    echo one two three  # no array literal needed

A sigil pair often changes the **lexer mode** to parse what's inside.

## Parse Options to Take Over `()`, `@`, and `=`

Most users don't have to worry about parse options.  Instead, they run either
`bin/osh` or `bin/ysh`, which are actually aliases for the same binary.  The
difference is that `bin/ysh` has the **option group** `ysh:all` on by default.

Nonetheless, here are two examples.

The `parse_at` option (in group `ysh:upgrade`) turns `@` into the **splice
operator** when it's at the front of a word:

```sh-prompt
$ var myarray = :| one two three |

$ echo @myarray         # @ isn't an an operator in shell
@myarray

$ shopt -s parse_at     # parse the @ symbol
$ echo @myarray
one two three

$ echo '@myarray'       # quote it to get the old behavior
@myarray
```

The `parse_equals` option (in group `ysh:all`) lets you omit `const`:

```sh-prompt
const x = 42 + a[i]     # accepted in OSH and Oil

shopt -s parse_equals   # Change the meaning of =

x = 42 + a[i]           # Means the same as above
                        # This is NOT a mutation.  It's a declaration.
```

## Static Parsing

POSIX specifies that Unix shell has multiple stages of parsing and evaluation.
For example:

```sh-prompt
$ x=2 
$ code='3 * x'
$ echo $(( code ))  # Silent eval of a string.  Dangerous!
6
```

Oil expressions are parsed in a single stage, and then evaluated, which makes
it more like Python or JavaScript:

```sh-prompt
$ setvar code = '3 * x'
$ echo $[ code ]
3 * x
```

Another example: shell assignment builtins like `readonly` and `local`
dynamically parsed, while Oil assignment like `const` and `var` are statically
parsed.

### Aside: Duplicate Functionality in Bash

It's confusing that [bash]($xref) has **both** statically- and
dynamically-parsed variants of the same functionality.

Boolean expressions:

- `[ -d /tmp ]` is dynamically parsed
- `[[ -d /tmp ]]` is statically parsed

C-style string literals:

- `echo -e '\n'` is dynamically parsed 
- `echo $'\n'` is statically parsed

<!--
Remaining dynamic parsing in shell:

- printf: `%.3f`
- glob: `*.py'`
- history lexer does another pass ...
-->

### Related Links

- [Parsing Bash is Undecidable](//www.oilshell.org/blog/2016/10/20.html)
- [A 30-year-old Security Problem](//www.oilshell.org/blog/2019/01/18.html#a-story-about-a-30-year-old-security-problem)
- [Comment on Perl and the rc shell](https://lobste.rs/s/7bpgbl/rc_plan_9_shell#c_mokqrn)

## Related Documents

- [Oil Language Influences](language-influences.html).  Where the syntax in Oil
  comes from.
- [Ideas for Future Deprecations](future.html).  Oil may grow its own command
  lexer mode.

## Appendix: Hand-Written vs. Generated Parsers

The [OSH language]($xref:osh-language) is parsed "by hand", while the [Oil
language]($xref:oil-language) is parsed with tables generated from a grammar (a
modified version of [Python's pgen]($xref:pgen2)).

This is mostly an implementation detail, but users may notice that OSH gives
more specific error messages!

Hand-written parsers give you more control over errors.  Eventually the Oil
language may have a hand-written parser as well.  Either way, feel free to file
bugs about error messages that confuse you.

