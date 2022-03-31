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
  Log('wwz.tsv')
  print(summary(wwz))
  Log('')

  wwz$date = as.POSIXct(wwz$date)

  wwz %>% arrange(date) -> wwz
  earliest = wwz$date[1]
  latest = wwz$date[nrow(wwz)]
  duration = latest - earliest

  Log('Summary: %d releases over %.1f days (%.1f years)', nrow(wwz), duration,
      duration / 365)
  Log('Average interval: %.1f days ', duration / nrow(wwz))

  n1 = nrow(wwz %>% filter(spec_wwz != '-'))
  Log('Number of spec.wwz: %d', n1)

  n2 = nrow(wwz %>% filter(survey_path != '-'))
  Log('Number of survey_path: %d', n2)

  n3 = nrow(wwz %>% filter(cpp_summary_path != '-'))
  Log('Number of cpp_summary_path: %d', n3)

  ctx$wwz = wwz

  Log('----')
  Log('spec.tsv')
  spec = read.delim(file.path(in_dir, 'spec.tsv'))
  print(summary(spec))
  Log('')

  spec$date = as.POSIXct(spec$release_date)

  Log('spec rows: %d', nrow(spec))

  n1 = nrow(spec %>% filter(!is.na(osh_py_passing)))
  Log('Number of osh_py_passing: %d', n1)

  n2 = nrow(spec %>% filter(!is.na(osh_cc_passing)))
  Log('Number of osh_cc_passing: %d', n2)


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

  long = gather(ctx$spec, implementation, num_passing, c('osh_py_passing', 'osh_cc_passing'))

  print(head(long))

  blueIndexLeft = which(long$version == '0.2.0' & long$implementation == 'osh_py_passing')
  redIndexLeft = which(long$version == '0.8.pre5' & long$implementation == 'osh_cc_passing')
  #indexRight = which(long$version == '0.9.9')

  Log('blueIndexLeft %d', blueIndexLeft)
  Log('redIndexLeft %d', redIndexLeft)
  #Log('indexRight %d', indexRight)

  long$label = NA

  # Label for readability
  long$label[blueIndexLeft] = sprintf(
    "v%s on %s\npassed %d tests in Python", long$version[blueIndexLeft],
    strftime(long$date[blueIndexLeft], format = '%Y-%m-%d'),
    long$num_passing[blueIndexLeft])

  long$label[redIndexLeft] = sprintf(
    "v%s on %s\npassed %d tests in C++", long$version[redIndexLeft],
    strftime(long$date[redIndexLeft], format = '%Y-%m-%d'),
    long$num_passing[redIndexLeft])

  print(head(long))
  ctx$long = long  # debugging

  g = ggplot(long, aes(date, num_passing, group = implementation,
                       color = implementation)) + 
    xlab('release date') +
    ylab('number of passing spec tests') +
    # Start from 0 spec tests
    ylim(0, NA) +
    theme(legend.position = 'bottom') +
    # lower luminance to make it darker
    scale_color_hue(labels = c('Fast Generated C++', 'Python Source (executable spec)'), l = 40) +
    ggtitle('Progress on the Middle-Out Implementation of https://oilshell.org',
            subtitle = "Weissman score: 99") +
    geom_line() +
    geom_point()

  g = g + geom_text(aes(label = label),
                    vjust = 2, hjust = 'inward', size = 5)

  # Fallow Period
  g = g + annotate("rect",
                   xmin = as.POSIXct('2020-08-01'),
                   xmax = as.POSIXct('2021-07-01'),
                   ymin = 600,
                   ymax = 1200,
                   alpha = 0.2)

  ctx$plot = g

  g
}

WriteAll = function(ctx, out_dir) {
  png_path = file.path(out_dir, 'spec-test-history.png')

  png(png_path, width=800, height=600)
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
