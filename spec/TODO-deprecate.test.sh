# TODO-deprecate: Code we want to get rid of!


#### oil:upgrade as alias for ysh:upgrade

shopt -p | grep simple_word
shopt --set oil:upgrade
shopt -p | grep simple_word

shopt --unset ysh:upgrade
shopt -p | grep simple_word

## STDOUT:
shopt -u simple_word_eval
shopt -s simple_word_eval
shopt -u simple_word_eval
## END


#### %() array literal

shopt --set parse_at

var x = %(one two)
echo @x

## STDOUT:
one two
## END
