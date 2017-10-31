#!/usr/bin/Rscript
#
# osh-parser.R -- Analyze output from shell scripts.
#
# Usage:
#   osh-parser.R OUT_DIR [TIMES_CSV...]

library(dplyr)
library(tidyr)

options(stringsAsFactors = F)

Log = function(fmt, ...) {
  cat(sprintf(fmt, ...))
  cat('\n')
}

main = function(argv) {
  out_dir = argv[[1]]

  hosts = list()
  for (i in 2:length(argv)) {
    times_path = argv[[i]]
    # Find it in the same directory
    lines_path = gsub('.times.', '.lines.', times_path, fixed = T)

    Log('times: %s', times_path)
    Log('lines: %s', lines_path)

    times = read.csv(times_path)
    lines = read.csv(lines_path)

    # Remove failures
    times %>% filter(status == 0) %>% select(-c(status)) -> times

    # Add the number of lines, joining on path, and compute lines/sec
    # TODO: Is there a better way compute lines_per_ms and then drop
    # lines_per_sec?
    times %>%
      left_join(lines, by = c('path')) %>%
      mutate(elapsed_ms = elapsed_secs * 1000,
             lines_per_ms = num_lines / elapsed_ms) %>%
      select(-c(elapsed_secs)) ->
      host_rows

    hosts[[i-1]] = host_rows
  }
  all_times = bind_rows(hosts)
  print(all_times)

  all_times %>% distinct(platform_id) -> distinct_hosts
  print(distinct_hosts)
  all_times %>% distinct(shell_id) -> distinct_shells
  print(distinct_shells)

  return()

  # Summarize rates by platform/shell
  all_times %>%
    group_by(shell_id, platform_id) %>%
    summarize(total_lines = sum(num_lines), total_ms = sum(elapsed_ms)) %>%
    mutate(lines_per_ms = total_lines / total_ms) ->
    rate_summary

  print(rate_summary)

  # Elapsed seconds for each shell by platform and file
  all_times %>%
    select(-c(lines_per_ms)) %>% 
    spread(key = shell_id, value = elapsed_ms) %>%
    arrange(platform_id, num_lines) ->
    elapsed
    #select(c(bash, dash, mksh, zsh, osh, num_lines, path)) ->

  Log('\n')
  Log('ELAPSED')
  print(elapsed)

  # Rates by file and shell
  all_times  %>%
    select(-c(elapsed_ms)) %>% 
    spread(key = shell_id, value = lines_per_ms) %>%
    arrange(platform_id, num_lines) ->
    rate
    #select(c(bash, dash, mksh, zsh, osh, num_lines, path)) ->

  Log('\n')
  Log('RATE')
  print(rate)

  write.csv(rate_summary,
            file.path(out_dir, 'rate_summary.csv'), row.names = F)
  write.csv(elapsed, file.path(out_dir, 'elapsed.csv'), row.names = F)
  write.csv(rate, file.path(out_dir, 'rate.csv'), row.names = F)

  Log('Wrote %s', out_dir)

  Log('PID %d done', Sys.getpid())
}

if (length(sys.frames()) == 0) {
  # increase ggplot font size globally
  #theme_set(theme_grey(base_size = 20))

  main(commandArgs(TRUE))
}
