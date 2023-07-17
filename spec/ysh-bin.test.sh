# Smoke test for the bin/ysh binary

## our_shell: ysh

#### Array func
write @[split('foo bar')]
## STDOUT:
foo
bar
## END


#### Options can be overridden
$SH -c 'shopt | grep parse_paren'
$SH +O parse_paren -c 'shopt | grep parse_paren'
## STDOUT:
shopt -s parse_paren
shopt -u parse_paren
## END
