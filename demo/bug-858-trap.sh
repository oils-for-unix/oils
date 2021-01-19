action() {
  echo "from signal"
}

trap "action" USR1

echo "Run: kill -USR1 $$; date"
while true; do
  date
	sleep 5 &
	wait $!
done
