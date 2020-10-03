---
in_progress: true
---

Ideas for Future Deprecations
=============================

These are some ideas, extracted from [Shell Language
Deprecations](deprecations.html).

These breakages may never happen, as they require a significant new lexer mode.
If they do, you will want to avoid the following syntax:

- `r'` and `c'` at the beginning of a word
- the character sequences `$/`, `'''`, `"""` anywhere

I expect that those sequences are rare, so this change would break few
programs.

<!-- cmark.py expands this -->
<div id="toc">
</div>


## Raw and C String Literals in Word Mode

We might want to make string literals in the command/word context match Oil's
expressions.  This means we have to disallow implicit concatenation, or certain
instances of it.

No:

    var x = foo'bar'   # Not a valid Oil expression
    echo foo'bar'      # Valid in shell, but discouraged

Yes:

    var x = 'foobar'
    echo 'foobar'

We don't want to break these, so = could be special

    ls --foo='with spaces'
    ls --foo="with $var"

New raw and C strings (which technically conflict with shell):

    echo r'\'   # equivalent to '\'
    echo c'\n'  # equivalent to $'\t'


## Multiline Strings and Redirects

Instead of here docs:

    cat <<EOF
    hello
    there, $name
    EOF

    cat <<'EOF'
    $5.99  # no interpolation
    'EOF'

We could have multiline strings:

    cat << """
    hello
    there, $name
    """

    cat << '''
    $5.99  # no interpolation
    '''

Minor breakage: the `'''` and `"""` tokens become significant.  It may also be
nice to change the meaning of `<<` slightly.

## First Class File Descriptors (`parse_amp`)

We want to make redirection simpler and more consistent.  We can remove the
confusing `<&` and `>&` operators, and instead use `>` and `<` with
descriptors.

Remains the same:

    echo foo >file
    read :var <file

Old:

    echo foo >& 2
    read var <& 0

New:

    echo foo > &2         # descriptor with &
    read :var < &0

    echo foo > &stderr    # named descriptor
    read :var < &stdin

Old:

    echo foo 1>& 2

New:

    echo foo &1 > &2

(Note: the syntax `{fd}> file.txt` will be replaced by the `open` builtin.)

<https://github.com/oilshell/oil/issues/673>

## Inline Eggex

Instead of:

    var pat = / digit+ /
    egrep $pat *.txt

You can imagine:

    egrep $/ digit+ / *.txt

Minor breakage: making `$/` significant.

## Bare Function Call

Instead of

    call f()
    call g(x, y)

You could do:

    f()   # calls a func, doesn't begin a shell function declaration
    g(x, y)

- This change probably doesn't involve a lexer mode.
- It would be a big breakage!

<!--

Idea: parse_square_brackets in lex_mode::OilCommand?

Instead of

    echo *.[ch]

You have to do

    echo @glob('*.[ch]')

Or even:

    echo @'*.[ch]'

Which is a small price to pay to free up []

Actually that's not bad... but

    echo *.py 
    still works

So then you can distinguish sigil pairs

EXPRESSION:

    :(1 + 2)
    &(1 + 2)

COMMAND:

    $[hostname] - bah!  conflicts   I guess the $(hostname) wart is OK?
        $<1+2> or $<a[i]>  # too ugly?
    @[seq 3]
    x = ^[echo $PWD]

    myarray = %[foo bar baz]

Yes I like this.  Doh might take ahwile.

Have to resolve $[1 + 2] and $[hostname].  We need another thing for expression
substitution.  It can't be $(1 + 2)

Maybe it's

    $$(1 + 2)   
    .(1 + 2)  
    ~(1 + 2)

    /(1 + 2)

That's a syntax error?


Globbing option:

if (x ~ @'*.py') {
}

if (x ~~ '*.py') {
}

Hm the latter still reads better.

-->

