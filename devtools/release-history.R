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

LoadAll = function(in_dir, ctx) {
  wwz = read.delim(file.path(in_dir, 'wwz.tsv'))
  Log('wwz rows: %d', nrow(wwz))

  n1 = nrow(wwz %>% filter(spec_wwz != '-'))
  Log('Number of spec.wwz: %d', n1)

  n2 = nrow(wwz %>% filter(survey_path != '-'))
  Log('Number of survey_path: %d', n2)

  n3 = nrow(wwz %>% filter(cpp_summary_path != '-'))
  Log('Number of cpp_summary_path: %d', n3)

  print(summary(wwz))

  ctx$wwz = wwz

  Log('----')


  spec = read.delim(file.path(in_dir, 'spec.tsv'))
  spec$date = as.POSIXct(spec$release_date)

  Log('spec rows: %d', nrow(spec))

  n1 = nrow(spec %>% filter(!is.na(osh_py_passing)))
  Log('Number of osh_py_passing: %d', n1)

  n2 = nrow(spec %>% filter(!is.na(osh_cc_passing)))
  Log('Number of osh_cc_passing: %d', n2)

  print(summary(spec))

  # Version errata:
  #
  # - 0.7.pre4 -- oil-* spec tests were somehow counted here, seems a bit buggy
  #   Delete it because it breaks the monotonicity of the graph
  # - 0.9.1 had stale benchmarks, but spec tests seem OK

  Log("Removing bad value in 0.7.pre4")
  spec[spec$version == "0.7.pre4", 'osh_py_passing'] = NA

  ctx$spec = spec

}

ProcessAll = function(ctx) {

  long = gather(ctx$spec, impl, num_passing, c('osh_py_passing', 'osh_cc_passing'))

  print(head(long))

  g = ggplot(long, aes(date, num_passing, group = impl, color = impl)) + 
    xlab('release date') +
    ylab('number of passing spec tests') +
    scale_color_hue(labels = c('Generated C++', 'Python source')) +
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
  in_dir = argv[[1]]
  out_dir = argv[[2]]

  ctx = new.env()

  LoadAll(in_dir, ctx)
  ProcessAll(ctx)
  WriteAll(ctx, out_dir)

  Log('PID %d done', Sys.getpid())
}

if (length(sys.frames()) == 0) {
  # increase ggplot font size globally
  theme_set(theme_grey(base_size = 20))

  main(commandArgs(TRUE))
}
