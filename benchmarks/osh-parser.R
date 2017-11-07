#!/usr/bin/Rscript
#
# osh-parser.R -- Analyze output from shell scripts.
#
# Usage:
#   osh-parser.R OUT_DIR [TIMES_CSV...]

library(dplyr)
library(tidyr)
library(stringr)

options(stringsAsFactors = F)

Log = function(fmt, ...) {
  cat(sprintf(fmt, ...))
  cat('\n')
}

sourceUrl = function(path) {
  sprintf('https://github.com/oilshell/oil/blob/master/%s', path)
}

main = function(argv) {
  out_dir = argv[[1]]

  # Merge all the inputs
  hosts = list()
  raw_times_list = list()
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
    raw_times_list[[i-1]] = times_path
  }

  all_times = bind_rows(hosts)
  print(summary(all_times))

  #
  # Find distinct shells and hosts, and label them for readability.
  #

  all_times %>% distinct(host_name, host_hash) -> distinct_hosts
  # Just use the name
  distinct_hosts$host_label = distinct_hosts$host_name
  print(distinct_hosts)


  all_times %>% distinct(shell_name, shell_hash) -> distinct_shells
  print(distinct_shells)

  distinct_shells$shell_label = NA  # the column we fill in below

  Log('Labeling shells')

  for (i in 1:nrow(distinct_shells)) {
    row = distinct_shells[i, ]
    if (row$shell_name == 'osh') {
      path = sprintf('../benchmark-data/shell-id/osh-%s/osh-version.txt',
                     row$shell_hash)
      Log('Reading %s', path)
      lines = readLines(path)
      if (length(grep('OVM', lines)) > 0) {
        label = 'osh-ovm'
      } else if (length(grep('CPython', lines)) > 0) {
        label = 'osh-cpython'
      }
    } else {  # same name for other shells
      label = row$shell_name
    }
    distinct_shells[i, ]$shell_label = label
  }               
  print(distinct_shells)

  # Replace name/hash combinations with labels.
  all_times %>%
    left_join(distinct_hosts, by = c('host_name', 'host_hash')) %>%
    left_join(distinct_shells, by = c('shell_name', 'shell_hash')) %>%
    select(-c(host_name, host_hash, shell_name, shell_hash)) ->
    all_times

  print(summary(all_times))
  print(head(all_times))

  # Summarize rates by platform/shell
  all_times %>%
    group_by(host_label, shell_label) %>%
    summarize(total_lines = sum(num_lines), total_ms = sum(elapsed_ms)) %>%
    mutate(lines_per_ms = total_lines / total_ms) ->
    shell_summary

  print(shell_summary)

  # Elapsed seconds for each shell by platform and file
  all_times %>%
    select(-c(lines_per_ms)) %>% 
    spread(key = shell_label, value = elapsed_ms) %>%
    arrange(host_label, num_lines) %>%
    mutate(filename = basename(path), filename_HREF = sourceUrl(path)) %>% 
    select(c(host_label, bash, dash, mksh, zsh, `osh-ovm`, `osh-cpython`,
             num_lines, filename, filename_HREF)) ->
    elapsed

  Log('\n')
  Log('ELAPSED')
  print(elapsed)

  # Rates by file and shell
  all_times  %>%
    select(-c(elapsed_ms)) %>% 
    spread(key = shell_label, value = lines_per_ms) %>%
    arrange(host_label, num_lines) %>%
    mutate(filename = basename(path), filename_HREF = sourceUrl(path)) %>% 
    select(c(host_label, bash, dash, mksh, zsh, `osh-ovm`, `osh-cpython`,
             num_lines, filename, filename_HREF)) ->
    rate

  Log('\n')
  Log('RATE')
  print(rate)

  # TODO: Set up cgit because Github links are slow.
  benchmarkDataLink = function(subdir, name, suffix) {
    #sprintf('../../../../benchmark-data/shell-id/%s', shell_id)
    sprintf('https://github.com/oilshell/benchmark-data/blob/master/%s/%s%s',
            subdir, name, suffix)
  }

  # Should be:
  # host_id_url
  # And then csv_to_html will be smart enough?  It should take --url flag?
  host_table = data_frame(
    host_label = distinct_hosts$host_label,
    host_id = paste(distinct_hosts$host_name,
                    distinct_hosts$host_hash, sep='-'),
    host_id_HREF = benchmarkDataLink('host-id', host_id, '/')
  )
  print(host_table)

  shell_table = data_frame(
    shell_label = distinct_shells$shell_label,
    shell_id = paste(distinct_shells$shell_name,
                     distinct_shells$shell_hash, sep='-'),
    shell_id_HREF = benchmarkDataLink('shell-id', shell_id, '/')
  )
  print(shell_table)

  raw_times = data_frame(
    filename = basename(as.character(raw_times_list)),
    filename_HREF = benchmarkDataLink('osh-parser', filename, '')
  )
  print(raw_times)

  writeCsv(host_table, file.path(out_dir, 'hosts'))
  writeCsv(shell_table, file.path(out_dir, 'shells'))
  writeCsv(raw_times, file.path(out_dir, 'raw_times'))
  writeCsv(shell_summary, file.path(out_dir, 'summary'))
  writeCsv(elapsed, file.path(out_dir, 'elapsed'))
  writeCsv(rate, file.path(out_dir, 'rate'))

  Log('Wrote %s', out_dir)

  Log('PID %d done', Sys.getpid())
}

# Write a CSV file along with a schema.
writeCsv = function(table, prefix) {
  data_out_path = paste0(prefix, '.csv')
  write.csv(table, data_out_path, row.names = F)

  fieldType = function(field_name) { typeof(table[[field_name]]) }

  types_list = lapply(names(table), fieldType)
  types = as.character(types_list)

  schema = data_frame(
    column_name = names(table),
    type = types
  )
  schema_out_path = paste0(prefix, '.schema.csv')
  write.csv(schema, schema_out_path, row.names = F)
}

if (length(sys.frames()) == 0) {
  # increase ggplot font size globally
  #theme_set(theme_grey(base_size = 20))

  main(commandArgs(TRUE))
}
