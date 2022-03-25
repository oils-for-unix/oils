#!/usr/bin/Rscript
#
# release-history.R

library(dplyr)
library(ggplot2)
library(tidyr)

options(stringsAsFactors = F)

Log = function(fmt, ...) {
  cat(sprintf(fmt, ...))
  cat('\n')
}

LoadAll = function(input, ctx) {
  d = read.delim(input)
  d$date = as.POSIXct(d$release_date)

  ctx$spec = d

  print(ctx$spec)
}

ProcessAll = function(ctx) {
  long = gather(ctx$spec, impl, num_passing, c('osh_py_passing', 'osh_cc_passing'))

  print(head(long))

  g = ggplot(long, aes(date, num_passing, group = impl, color = impl)) + 
    xlab('release date') +
    ylab('number of passing spec tests') +
    scale_color_hue(labels = c('C++', 'Python')) +
    ggtitle('Progress on the Middle-Out Implementation of OSH') +
    geom_line() +
    geom_point()

  ctx$plot = g

  g
}

WriteAll = function(ctx, out_dir) {
  png_path = file.path(out_dir, 'spec_test_history.png')

  png(png_path, width=1000, height=600)
  print(ctx$plot)
  dev.off()
  Log('Wrote %s', png_path)
}

main = function(argv) {
  input = argv[[1]]
  output = argv[[2]]

  ctx = new.env()

  LoadAll(input, ctx)
  ProcessAll(ctx)
  WriteAll(ctx, output)

  Log('PID %d done', Sys.getpid())
}

if (length(sys.frames()) == 0) {
  # increase ggplot font size globally
  theme_set(theme_grey(base_size = 20))

  main(commandArgs(TRUE))
}
