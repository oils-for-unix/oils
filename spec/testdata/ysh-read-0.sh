
echo 'read -r'
seq 2 | {
  read -r
  echo reply=$REPLY

  read -r
  echo reply=$REPLY
}
echo

echo 'read --line'
seq 2 | {
  read --line
  echo line=$_line

  read --line
  echo line=$_line
}
echo

echo 'Mixed'
seq 4 | {
  read -r
  echo reply=$REPLY

  read -r
  echo reply=$REPLY

  read --line
  echo line=$_line

  read -r
  echo reply=$REPLY
}
