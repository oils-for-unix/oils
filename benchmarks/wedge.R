#!/usr/bin/env Rscript
#
# wedge.R -- Show how long it takes
#
# Usage:
#   wedge.R ACTION IN_DIR OUT_DIR

library(dplyr)
library(ggplot2)

source('benchmarks/common.R')

options(stringsAsFactors = F,
        # Make the report wide.  tibble.width doesn't appear to do this?
        width=200,
        #tibble.print_max=Inf,

        # for printing of timestamps
        digits=11
)

WritePlot <- function(p, filename, width = 800, height = 600) {
  png(filename, width=width, height=height)
  plot(p)
  dev.off()
  Log('Wrote %s', filename)
}

PlotElapsed <- function(ctx) {
  g <- ggplot(ctx$tasks, aes(x = wedge, y = elapsed_secs))

  # NOTE: stat = "identity" required for x and y, geom_bar makes a histogram by
  # default
  b <- geom_bar(stat = "identity")
  t <- ggtitle('Elapsed Time')

  g + b + t #+ scale_fill_manual(values=palette)
}

PlotXargs <- function(ctx) {
  tasks = ctx$tasks

  left = min(tasks$start_time)
  Log("Starting at %f", left)

  tasks$start_time = tasks$start_time - left
  tasks$end_time = tasks$end_time - left
  #print(tasks)

  g = ggplot(tasks, aes(x = start_time, xend = end_time, y = xargs_slot, yend = xargs_slot))
  line = geom_segment(linewidth = 10, aes(color = wedge))
  labs = labs(title = "Parallel Wedge Builds", x = "time (seconds)", y = "xargs slot")

  g + line + labs

  # Doesn't work
  #+ scale_x_time()
}

# Something like this
# https://stackoverflow.com/questions/70767351/plotting-date-intervals-in-ggplot2

Report = function(ctx, out_dir) {
  p = PlotElapsed(ctx)

  p = PlotElapsed(ctx)
  WritePlot(p, file.path(out_dir, 'elapsed.png'))

  p = PlotXargs(ctx)
  WritePlot(p, file.path(out_dir, 'xargs.png'))
}

Load = function(in_dir) {
  list(tasks = read.table(file.path(in_dir, 'tasks.tsv'), header=T))
}

main = function(argv) {
  action = argv[[1]]

  if (action == 'xargs-report') {
    in_dir = argv[[2]]
    out_dir = in_dir  # same for now

    ctx = Load(in_dir)
    Report(ctx, out_dir)

  } else {
    Log("Invalid action '%s'", action)
    quit(status = 1)
  }
}

if (length(sys.frames()) == 0) {
  # increase ggplot font size globally
  theme_set(theme_grey(base_size = 20))
  main(commandArgs(TRUE))
}
