#!/bin/bash
# COMPOUND here docs mixed with individual here docs
# This shows it has to be a depth first search, but POST ORDER TRAVERSAL.
while cat <<EOF1; read line; do echo "  -> line: '$line'"; cat <<EOF2; done <<EOF3
condition here doc
EOF1
  body here doc
EOF2
while loop here doc 1
while loop here doc 2
EOF3
