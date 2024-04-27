## oils_failures_allowed: 1

#### help topics that are embedded
help > help.txt
echo no args $?

for topic in help oils-usage {osh,ysh}-usage {osh,ysh}-chapters; do
  help $topic > $topic.txt
  echo $topic $?
done

help zz > zz.txt
echo zz $?
## STDOUT:
no args 0
help 0
oils-usage 0
osh-usage 0
ysh-usage 0
osh-chapters 0
ysh-chapters 0
zz 1
## END

#### help topics that are linked
help command-sub | grep -o chap-word-lang.html
echo status=$?

help read | grep -o chap-builtin-cmd.html
echo status=$?

## STDOUT:
chap-word-lang.html
status=0
chap-builtin-cmd.html
status=0
## END

#### help shows 'ysh-chapters' topic

# doesn't show ANSI text unless TTY
help | grep ysh-chapters

echo status=$?

## STDOUT:
TODO fix dev-minimal ~~~ ysh-chapters ~~~
status=0
## END

