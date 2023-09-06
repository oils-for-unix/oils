mainfunc() {
  source spec/testdata/bash-source-pushtemp.sh "$@"
}

main2() {
  mainfunc a b
}

main1() {
  main2
}

main1
