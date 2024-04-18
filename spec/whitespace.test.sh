## oils_failures_allowed: 2
## compare_shells: dash bash mksh zsh ash

#### Parsing shell words \r \v

# frontend/lexer_def.py has rules for this

tab=$(python2 -c 'print "argv.py -\t-"')
cr=$(python2 -c 'print "argv.py -\r-"')
vert=$(python2 -c 'print "argv.py -\v-"')
ff=$(python2 -c 'print "argv.py -\f-"')

$SH -c "$tab"
$SH -c "$cr"
$SH -c "$vert"
$SH -c "$ff"

## STDOUT:
['-', '-']
['-\r-']
['-\x0b-']
['-\x0c-']
## END

#### \r at end of line is not special

# hm I wonder if Windows ports have rules for this?

cr=$(python2 -c 'print "argv.py -\r"')

$SH -c "$cr"

## STDOUT:
['-\r']
## END

#### Default IFS does not include \r \v \f

# dash and zsh don't have echo -e
tab=$(python2 -c 'print "-\t-"')
cr=$(python2 -c 'print "-\r-"')
vert=$(python2 -c 'print "-\v-"')
ff=$(python2 -c 'print "-\f-"')

$SH -c 'argv.py $1' dummy0 "$tab"
$SH -c 'argv.py $1' dummy0 "$cr"
$SH -c 'argv.py $1' dummy0 "$vert"
$SH -c 'argv.py $1' dummy0 "$ff"

## STDOUT:
['-', '-']
['-\r-']
['-\x0b-']
['-\x0c-']
## END

# No word splitting in zsh

## OK zsh STDOUT:
['-\t-']
['-\r-']
['-\x0b-']
['-\x0c-']
## END
