echo '{ }' | j8 read
= _reply

exit

echo '{"k": "v"}' | j8 read
= _reply

#exit

echo '{"k": null}' | j8 read
= _reply

#exit

echo '{"k": 1, "k2": 2}' | j8 read
= _reply

#exit

echo '{"k": {"k2": null}}' | j8 read
= _reply

#exit

echo '{"k": {"k2": "v2"}, "k3": null}' | j8 read
= _reply
