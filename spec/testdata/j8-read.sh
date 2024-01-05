echo '{ }' | json8 read
pp line (_reply)

echo '[ ]' | json8 read
pp line (_reply)

echo '[42]' | json8 read
pp line (_reply)

echo '[true, false]' | json8 read
pp line (_reply)

echo '{"k": "v"}' | json8 read
pp line (_reply)

echo '{"k": null}' | json8 read
pp line (_reply)

echo '{"k": 1, "k2": 2}' | json8 read
pp line (_reply)

echo "{u'k': {b'k2': null}}" | json8 read
pp line (_reply)

echo '{"k": {"k2": "v2"}, "k3": "backslash \\ \" \n line 2 \u03bc "}' | json8 read
pp line (_reply)

json8 read (&x) <<'EOF'
{u'k': {u'k2': u'v2'}, u'k3': u'backslash \\ \" \n line 2 \u{3bc} '}
EOF
pp line (x)
