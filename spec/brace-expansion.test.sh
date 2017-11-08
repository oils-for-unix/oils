#!/usr/bin/env bash

### no expansion
echo {foo}
# stdout: {foo}

### incomplete trailing expansion
echo {a,b}_{
# stdout: a_{ b_{
# OK osh stdout: {a,b}_{

### partial leading expansion
echo }_{a,b}
# stdout: }_a }_b
# OK osh stdout: }_{a,b}

### partial leading expansion 2
echo {x}_{a,b}
# stdout: {x}_a {x}_b
# OK osh stdout: {x}_{a,b}

### } in expansion
# hm they treat this the SAME.  Leftmost { is matched by first }, and then
# there is another } as the postfix.
echo {a,b}}
# stdout: a} b}
# status: 0
# OK osh stdout: {a,b}}
# OK zsh stdout-json: ""
# OK zsh status: 1

### single expansion
echo {foo,bar}
# stdout: foo bar

### double expansion
echo {a,b}_{c,d}
# stdout: a_c a_d b_c b_d

### triple expansion
echo {0,1}{0,1}{0,1}
# stdout: 000 001 010 011 100 101 110 111

### double expansion with single and double quotes
echo {'a',b}_{c,"d"}
# stdout: a_c a_d b_c b_d

### expansion with mixed quotes
echo -{\X"b",'cd'}-
# stdout: -Xb- -cd-

### expansion with simple var
a=A
echo -{$a,b}-
# stdout: -A- -b-

### double expansion with simple var -- bash bug
# bash is inconsistent with the above
a=A
echo {$a,b}_{c,d}
# stdout: A_c A_d b_c b_d
# BUG bash stdout: b_c b_d

### double expansion with braced variable
# This fixes it
a=A
echo {${a},b}_{c,d}
# stdout: A_c A_d b_c b_d

### double expansion with literal and simple var
a=A
echo {_$a,b}_{c,d}
# stdout: _A_c _A_d b_c b_d
# BUG bash stdout: _ _ b_c b_d

### expansion with command sub
a=A
echo -{$(echo a),b}-
# stdout: -a- -b-

### expansion with arith sub
a=A
echo -{$((1 + 2)),b}-
# stdout: -3- -b-

### double expansion with escaped literals
a=A
echo -{\$,\[,\]}-
# stdout: -$- -[- -]-

### { in expansion
# bash and mksh treat this differently.  bash treats the
# first { is a prefix.  I think it's harder to read, and \{{a,b} should be
# required.
echo {{a,b}
# stdout: {{a,b}
# BUG bash/zsh stdout: {a {b

### quoted { in expansion
echo \{{a,b}
# stdout: {a {b

### Empty expansion
echo a{X,,Y}b
# stdout: aXb ab aYb

### Empty alternative
# zsh and mksh don't do word elision, probably because they do brace expansion
# AFTER variable substitution.
argv.py {X,,Y,}
# stdout: ['X', 'Y']
# OK mksh/zsh stdout: ['X', '', 'Y', '']
# status: 0

### Empty alternative with empty string suffix
# zsh and mksh don't do word elision, probably because they do brace expansion
# AFTER variable substitution.
argv.py {X,,Y,}''
# stdout: ['X', '', 'Y', '']
# status: 0

### nested brace expansion
echo -{A,={a,b}=,B}-
# stdout: -A- -=a=- -=b=- -B-

### triple nested brace expansion
echo -{A,={a,.{x,y}.,b}=,B}-
# stdout: -A- -=a=- -=.x.=- -=.y.=- -=b=- -B-

### nested and double brace expansion
echo -{A,={a,b}{c,d}=,B}-
# stdout: -A- -=ac=- -=ad=- -=bc=- -=bd=- -B-

### expansion on RHS of assignment
# I think bash's behavior is more consistent.  No splitting either.
v={X,Y}
echo $v
# stdout: {X,Y}
# BUG mksh stdout: X Y

### no expansion with RHS assignment
{v,x}=X
# status: 127
# stdout-json: ""
# OK zsh status: 1

### Tilde expansion
HOME=/home/foo
echo ~
HOME=/home/bar
echo ~
# stdout-json: "/home/foo\n/home/bar\n"

### Tilde expansion with brace expansion
# The brace expansion happens FIRST.  After that, the second token has tilde
# FIRST, so it gets expanded.  The first token has an unexpanded tilde, because
# it's not in the leading position.
# NOTE: mksh gives different behavior!  So it probably doesn't matter that
# much...
HOME=/home/bob
echo {foo~,~}/bar
# stdout: foo~/bar /home/bob/bar
# OK mksh stdout: foo~/bar ~/bar

### Two kinds of tilde expansion
# ~/foo and ~bar
HOME=/home/bob
echo ~{/src,root}
# stdout: /home/bob/src /root
# OK mksh stdout: ~/src ~root

### Tilde expansion come before var expansion
HOME=/home/bob
foo=~
echo $foo
foo='~'
echo $foo
# In the second instance, we expand into a literal ~, and since var expansion
# comes after tilde expansion, it is NOT tried again.
# stdout-json: "/home/bob\n~\n"

### Number range expansion
echo -{1..8..3}-
# stdout: -1- -4- -7-
# N-I mksh stdout: -{1..8..3}-

### Ascending number range expansion with negative step
echo -{1..8..-3}-
# stdout: -1- -4- -7-
# OK zsh stdout: -7- -4- -1-
# N-I mksh stdout: -{1..8..-3}-

### Descending number range expansion
echo -{8..1..3}-
# stdout: -8- -5- -2-
# N-I mksh stdout: -{8..1..3}-

### Descending number range expansion with negative step
echo -{8..1..-3}-
# stdout: -8- -5- -2-
# OK zsh stdout: -2- -5- -8-
# N-I mksh stdout: -{8..1..-3}-

### Char range expansion
echo -{a..e}-
# stdout: -a- -b- -c- -d- -e-
# N-I mksh stdout: -{a..e}-

### Char range expansion with step
echo -{a..e..2}- -{a..e..-2}-
# stdout: -a- -c- -e- -a- -c- -e-
# N-I mksh/zsh stdout: -{a..e..2}- -{a..e..-2}-

### Descending char range expansion
echo -{e..a..2}- -{e..a..-2}-
# stdout: -e- -c- -a- -e- -c- -a-
# N-I mksh/zsh stdout: -{e..a..2}- -{e..a..-2}-

### Fixed width number range expansion
echo -{01..03}-
# stdout: -01- -02- -03-
# N-I mksh stdout: -{01..03}-

### Inconsistent fixed width number range expansion
# zsh uses the first one, bash uses the max width?
echo -{01..003}-
# stdout: -001- -002- -003-
# OK zsh stdout: -01- -02- -03-
# N-I mksh stdout: -{01..003}-

### Inconsistent fixed width number range expansion
# zsh uses the first width, bash uses the max width?
echo -{01..3}-
# stdout: -01- -02- -03-
# N-I mksh stdout: -{01..3}-

### Side effect in expansion
# bash is the only one that does it first.  I guess since this is
# non-POSIX anyway, follow bash?
i=0
echo {a,b,c}-$((i++))
# stdout: a-0 b-1 c-2
# OK mksh/zsh stdout: a-0 b-0 c-0
