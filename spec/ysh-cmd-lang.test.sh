## our_shell: ysh

#### Redirect with if, case, while, for

if (true) {
  echo ysh-if
} > out

cat out

case (true) {
  (true) {
    echo ysh-case
  }
} > out

cat out

while (true) {
  echo ysh-while
  break
} > out

cat out

for x in ([42]) {
  echo ysh-for
} > out

cat out

## STDOUT:
ysh-if
ysh-case
ysh-while
ysh-for
## END

