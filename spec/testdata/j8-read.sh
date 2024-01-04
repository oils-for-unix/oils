echo '{ }' | j8 read
pp line (_reply)

echo '[ ]' | j8 read
pp line (_reply)

echo '[42]' | j8 read
pp line (_reply)

echo '[true, false]' | j8 read
pp line (_reply)

echo '{"k": "v"}' | j8 read
pp line (_reply)

echo '{"k": null}' | j8 read
pp line (_reply)

echo '{"k": 1, "k2": 2}' | j8 read
pp line (_reply)

echo "{u'k': {b'k2': null}}" | j8 read
pp line (_reply)

echo '{"k": {"k2": "v2"}, "k3": "backslash \\ \" \n line 2 \u03bc "}' | j8 read
pp line (_reply)

j8 read (&x) <<'EOF'
{u'k': {u'k2': u'v2'}, u'k3': u'backslash \\ \" \n line 2 \u{3bc} '}
EOF
pp line (x)
