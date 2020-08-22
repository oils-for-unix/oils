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
var x = @(seq 3)

shopt -s parse_at
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
shopt -s oil:basic

for x in @(seq 3) {
  echo "[$x]"
}
for x in @(seq 3) {
  argv.py z [$x]  # note this is an empty glob!!!
}
## STDOUT:
[1]
[2]
[3]
['z']
['z']
['z']
## END
