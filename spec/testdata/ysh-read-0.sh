
echo 'read -r'
seq 2 | {
  read -r
  echo REPLY=$REPLY

  read -r
  echo REPLY=$REPLY
}
echo

echo 'read --line'
seq 2 | {
  read --line
  echo _reply=$_reply

  read --line
  echo _reply=$_reply
}
echo

echo 'Mixed'
seq 4 | {
  read -r
  echo REPLY=$REPLY

  read -r
  echo REPLY=$REPLY

  read --line
  echo _reply=$_reply

  read -r
  echo REPLY=$REPLY
}
