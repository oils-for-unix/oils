#!/usr/bin/Rscript
#
# osh-parser.R
#
# Analyze output from shell scripts.

library(dplyr)
library(tidyr)

Log = function(fmt, ...) {
  cat(sprintf(fmt, ...))
  cat('\n')
}

main = function(argv) {
  # num_lines, path
  lines = read.csv(argv[[1]])

  # status, elapsed, shell, path
  times = read.csv(argv[[2]])

  out_dir = argv[[3]]

  # TODO:
  # - compute lines per second for every cell?

  #print(lines)
  #print(times)

  # Remove failures
  times %>% filter(status == 0) %>% select(-c(status)) -> times

  # Add the number of lines, joining on path, and compute lines/sec
  # TODO: Is there a better way compute lines_per_ms and then drop lines_per_sec?
  times %>%
    left_join(lines, by = c('path')) %>%
    mutate(elapsed_ms = elapsed_secs * 1000,
           lines_per_ms = num_lines / elapsed_ms) %>%
    select(-c(elapsed_secs)) ->
    joined
  #print(joined)

  # Summarize rates
  joined %>%
    group_by(shell) %>%
    summarize(total_lines = sum(num_lines), total_ms = sum(elapsed_ms)) %>%
    mutate(lines_per_ms = total_lines / total_ms) ->
    rate_summary

  # Put OSH last!
  first = rate_summary %>% filter(shell != 'osh')
  last = rate_summary %>% filter(shell == 'osh')
  rate_summary = bind_rows(list(first, last))
  print(rate_summary)

  # Elapsed seconds by file and shell
  joined %>%
    select(-c(lines_per_ms)) %>% 
    spread(key = shell, value = elapsed_ms) %>%
    arrange(num_lines) %>%
    select(c(bash, dash, mksh, zsh, osh, num_lines, path)) ->
    elapsed
  print(elapsed)

  # Rates by file and shell
  joined %>%
    select(-c(elapsed_ms)) %>% 
    spread(key = shell, value = lines_per_ms) %>%
    arrange(num_lines) %>%
    select(c(bash, dash, mksh, zsh, osh, num_lines, path)) ->
    rate
  print(rate)

  write.csv(elapsed, file.path(out_dir, 'elapsed.csv'), row.names = F)
  write.csv(rate, file.path(out_dir, 'rate.csv'), row.names = F)
  write.csv(rate_summary, file.path(out_dir, 'rate_summary.csv'), row.names = F)

  Log('Wrote %s', out_dir)

  Log('PID %d done', Sys.getpid())
}

if (length(sys.frames()) == 0) {
  # increase ggplot font size globally
  #theme_set(theme_grey(base_size = 20))

  main(commandArgs(TRUE))
}
