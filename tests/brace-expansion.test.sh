#!/bin/bash

### no expansion
echo {foo}
# stdout: {foo}

### expansion
echo {foo,bar}
# stdout: foo bar

### double expansion
echo {a,b}_{c,d}
# stdout: a_c a_d b_c b_d

### { in expansion
# bash and mksh treat this differently.  bash treats the
# first { is a prefix.  I think it's harder to read, and \{{a,b} should be
# required.
echo {{a,b}
# stdout: {{a,b}
# BUG bash stdout: {a {b

### quoted { in expansion
echo \{{a,b}
# stdout: {a {b

### } in expansion
# hm they treat this the SAME.  Leftmost { is matched by first }, and then
# there is another } as the postfix.
echo {a,b}}
# stdout: a} b}

### Empty expansion
echo a{X,,Y}b
# stdout: aXb ab aYb

### nested brace expansion
echo X{A,x{a,b}y,B}Y
# stdout: XAY XxayY XxbyY XBY

### expansion on RHS of assignment
# I think bash's behavior is more consistent.  No splitting either.
v={X,Y}
echo $v
# stdout: {X,Y}
# BUG mksh stdout: X Y

### no expansion with RHS assignment
{v,x}=X
# status: 127

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
