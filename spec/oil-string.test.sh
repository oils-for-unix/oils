#### C strings in %() array literals
shopt -s oil:basic

var lines=%($'aa\tbb' $'cc\tdd')
write @lines

## STDOUT:
aa	bb
cc	dd
## END

#### single quoted -- implicit and explicit raw
var x = 'foo bar'
echo $x
setvar x = r'foo bar'  # Same string
echo $x
setvar x = r'\t\n'  # This is raw
echo $x
## STDOUT:
foo bar
foo bar
\t\n
## END

#### Implicit raw single quote with backslash is a syntax error
var x = '\t\n'
echo $x
## status: 2
## stdout-json: ""

#### single quoted C strings: c'foo\n' and $'foo\n'
var x = c'foo\nbar'
echo "$x"
var y = $'foo\nbar'
echo "$y"
## STDOUT:
foo
bar
foo
bar
## END

