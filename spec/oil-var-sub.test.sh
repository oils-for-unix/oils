# oil-var-sub.test.sh

#### ${x|html}
x='echo hi 2>&1'
echo "${x|html}"
## STDOUT:
echo hi 2&gt;&amp;1
## END

#### ${x %05d}
x=3
printf '%05d\n' "$x"
echo ${x %05d}
## STDOUT:
00003
00003
## END

#### ${.myproc builtin sub}

proc myproc() {
  echo "$@"
}

echo ${.myproc builtin sub}
## STDOUT:
builtin sub
## END

#### $[x] with _ESCAPER
shopt --set oil:basic

x='echo hi 2>&1'

push --temp _ESCAPER=html {
  echo "code $[x]"
}

# No _ESCAPER: fatal error
echo "code $[x]"

## STDOUT:
code echo hi 2&gt;&amp;1
## END

