
echo 'read -r'
seq 2 | {
  read -r
  echo REPLY=$REPLY

  read -r
  echo REPLY=$REPLY
}
echo

echo 'read --raw-line'
seq 2 | {
  read --raw-line
  echo _reply=$_reply

  read --raw-line
  echo _reply=$_reply
}
echo

echo 'Mixed'
seq 4 | {
  read -r
  echo REPLY=$REPLY

  read -r
  echo REPLY=$REPLY

  read --raw-line
  echo _reply=$_reply

  read -r
  echo REPLY=$REPLY
}
