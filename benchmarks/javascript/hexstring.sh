#!/bin/bash

hexdigits='0123456789abcdef'
for c in {0..9} {a..f}; do
  for d in {0..9} {a..f}; do
    for e in {0..9} {a..f}; do
      hexbyte=$c$d$e

      byte=$hexbyte
      byte=${byte//0/0000}
      byte=${byte//1/0001}
      byte=${byte//2/0010}
      byte=${byte//3/0011}

      byte=${byte//4/0100}
      byte=${byte//5/0101}
      byte=${byte//6/0110}
      byte=${byte//7/0111}

      byte=${byte//8/1000}
      byte=${byte//9/1001}
      byte=${byte//a/1010}
      byte=${byte//b/1011}

      byte=${byte//c/1100}
      byte=${byte//d/1101}
      byte=${byte//e/1110}
      byte=${byte//f/1111}

      #echo $byte)

      ones=${byte//0/}
      if test ${#ones} -eq 11; then
        echo $hexbyte $byte
      fi
    done
  done
done
