#!/bin/bash

n=1000
x=10000

main() {
  for ((i = 0; i < n; ++i)) {
    for ((j = i; j < n; ++j)) {
      if (( i*i + j*j == x )); then
        echo $i $j
      fi
    }
  }
}

main
