# Demo of redirecting from a here doc.
#
# All shells support this when passed a filename.  But they all mess up
# when passed this code on stdin, because they simultaneously try to read from
# stdin!

exec <<EOF
one
two
three
EOF

read x
echo "x=$x"
read y
echo "y=$y"
#read z
#echo "z=$z"
echo DONE
