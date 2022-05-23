# spec/oil-case

#### case x -- parse_bare_word

case x in 
  (*.py)
    echo 'Python'
    ;;
esac

## status: 2
## STDOUT:
## END

#### case $x in (test) -- parse_bare_word

var x = 'build'

case $x in 
  ('build') echo 'build' ;;
  (test) echo 'test' ;;
  (*) echo 'other' ;;
esac

## status: 2
## STDOUT:
## END
