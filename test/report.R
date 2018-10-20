#!/usr/bin/env Rscript
#
# report.R

library(dplyr)

options(stringsAsFactors = F)

source('benchmarks/common.R')

UnitTestReport = function(in_dir, out_dir) {
  tasks = read.csv(file.path(in_dir, 'tasks.csv'))

  tasks %>% filter(status != 0) -> failed
  if (nrow(failed) != 0) {
    print(failed)
    stop('Some tasks failed')
  }

  tasks %>% 
    mutate(elapsed_ms = elapsed_secs * 1000) %>%
    select(-c(status, elapsed_secs)) %>%
    select(c(elapsed_ms, test, test_HREF)) ->
    tasks

  precision = SamePrecision(0)
  writeCsv(tasks, file.path(out_dir, 'report'), precision)
}

main = function(argv) {
  action = argv[[1]]
  in_dir = argv[[2]]
  out_dir = argv[[3]]

  if (action == 'unit') {
    UnitTestReport(in_dir, out_dir)

  } else if (action == 'spec') {
    # TODO

  } else {
    Log("Invalid action '%s'", action)
    quit(status = 1)
  }
  Log('PID %d done', Sys.getpid())
}


if (length(sys.frames()) == 0) {
  # increase ggplot font size globally
  #theme_set(theme_grey(base_size = 20))

  main(commandArgs(TRUE))
}
