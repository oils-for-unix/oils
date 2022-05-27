# TODO-depreate: Code we want to get rid of!


#### oil:basic as alias for oil:upgrade

shopt -p | grep simple_word
shopt --set oil:basic
shopt -p | grep simple_word

## STDOUT:
shopt -u simple_word_eval
shopt -s simple_word_eval
## END

