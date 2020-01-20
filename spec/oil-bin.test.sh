# Smoke test for the bin/oil binary

#### Array func
func a(x) { return @(1 2 $x) }
write @a(42)
## STDOUT:
1
2
42
## END


#### Options can be overridden
$SH -c 'shopt | grep parse_paren'
$SH +O parse_paren -c 'shopt | grep parse_paren'
## STDOUT:
shopt -s parse_paren
shopt -u parse_paren
## END
