#!/usr/bin/env Rscript
#
# wedge.R -- Show how long it takes
#
# Usage:
#   wedge.R ACTION IN_DIR OUT_DIR

library(dplyr)
# Hm this isn't available
#library(ggplot2)

source('benchmarks/common.R')

options(stringsAsFactors = F,
        # Make the report wide.  tibble.width doesn't appear to do this?
        width=200,
        tibble.print_max=Inf
)

Report = function(ctx) {
  print(ctx$tasks)
  Log('hi')

  # TODO: geom_segment for start and end?
  # with xargs_slot
  #
  # Something like this
  # https://stackoverflow.com/questions/70767351/plotting-date-intervals-in-ggplot2
}

Load = function(in_dir) {
  list(
       tasks = read.table(file.path(in_dir, 'tasks.tsv'), header=T)
       )
}

main = function(argv) {
  action = argv[[1]]

  if (action == 'xargs-report') {
    in_dir = argv[[2]]
    out_dir = argv[[3]]
    ctx = Load(in_dir)
    Report(ctx)

  } else {
    Log("Invalid action '%s'", action)
    quit(status = 1)
  }
}

if (length(sys.frames()) == 0) {
  # increase ggplot font size globally
  #theme_set(theme_grey(base_size = 20))
  main(commandArgs(TRUE))
}
