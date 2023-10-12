# @( conflict

#### extglob
shopt -s extglob

[[ foo.py == @(*.sh|*.py) ]]
echo status=$?

# Synonym.  This is a syntax error in bash.
[[ foo.py == ,(*.sh|*.py) ]]
echo status=$?

## STDOUT:
status=0
status=0
## END

#### split command sub @() in expression mode
shopt --set parse_proc parse_at

var x = @(seq 3)

write -- @x
## STDOUT:
1
2
3
## END

#### split command sub @() in command mode

shopt -s parse_at
write -- @(seq 3)

echo --
IFS=x
x=axbxxc
argv.py $x

# This construct behaves the same with simple_word_eval on
echo --
shopt -s simple_word_eval
write -- @(seq 3)


echo --
write -- @(echo axbxxc)

## STDOUT:
1
2
3
--
['a', 'b', '', 'c']
--
1
2
3
--
a
b

c
## END

#### Idiomatic for loop using @(seq $n)
shopt -s oil:upgrade

for x in @(seq 3) {
  echo "[$x]"
}
for x in @(seq 3) {
  argv.py z @[glob("[$x]")]
}
## STDOUT:
[1]
[2]
[3]
['z']
['z']
['z']
## END

#### @() can't start in the middle of the word
shopt -s extglob  # this makes it match in bash
shopt -s oil:upgrade

# This is currently a RUNTIME error when simple_word_eval is on

touch foo.py
echo f@(*.py)
## status: 1
## STDOUT:
## END
## OK bash status: 0
## OK bash STDOUT:
foo.py
## END

#### @() can't have any tokens after it
shopt -s oil:upgrade

write -- @(seq 2)
write -- @(seq 3)x
## status: 2
## STDOUT:
1
2
## END
