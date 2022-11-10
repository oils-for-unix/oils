#!/usr/bin/Rscript
#
# benchmarks/report_test.R

source('benchmarks/report.R')

library(RUnit)

TestShellLabels = function() {
  shell_name = '_bin/cxx-opt/osh_eval.stripped'
  shell_hash = 'abcdef'
  d = data.frame(shell_hash = c('abcdef'))

  label = ShellLabels(shell_name, shell_hash, 1)
  checkEquals('opt/osh_eval', label)

  shell_name = 'yy/zz/_bin/cxx-opt/osh_eval.stripped'
  label = ShellLabels(shell_name, shell_hash, 1)
  checkEquals('opt/osh_eval', label)

  shell_name = 'yy/zz/_bin/cxx-bumpleak/osh_eval'
  label = ShellLabels(shell_name, shell_hash, 1)
  checkEquals('bumpleak/osh_eval', label)
}

main = function(argv) {
  TestShellLabels()
}

if (length(sys.frames()) == 0) {
  main(commandArgs(TRUE))
}
