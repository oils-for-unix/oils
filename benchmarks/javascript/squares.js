#!/usr/bin/env node

var n = 1000
var x = 10000

function main() {
  for (var i = 0; i < n; ++i) {
    for (var j = i; j < n; ++j) {
      if (i*i + j*j == x) {
        console.log(i, j)
      }
    }
  }
}

main()
