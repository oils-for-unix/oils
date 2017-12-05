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

# Takes a filename, not a path.
sourceUrl2 = function(filename) {
  sprintf(
      'https://github.com/oilshell/oil/blob/master/benchmarks/testdata/%s',
      filename)
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

ParserReport = function(in_dir, out_dir) {
  times = read.csv(file.path(in_dir, 'times.csv'))
  lines = read.csv(file.path(in_dir, 'lines.csv'))
  raw_data = read.csv(file.path(in_dir, 'raw-data.csv'))
  vm = read.csv(file.path(in_dir, 'virtual-memory.csv'))

  # For joining by filename
  lines_by_filename = data_frame(
      num_lines = lines$num_lines,
      filename = basename(lines$path)
  )

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
    all_times

  #print(head(times))
  #print(head(lines))
  #print(head(vm))
  #print(head(all_times))

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

  Log('summary(all_times):')
  print(summary(all_times))
  Log('head(all_times):')
  print(head(all_times))

  # Summarize rates by platform/shell
  all_times %>%
    group_by(host_label, shell_label) %>%
    summarize(total_lines = sum(num_lines), total_ms = sum(elapsed_ms)) %>%
    mutate(lines_per_ms = total_lines / total_ms) ->
    shell_summary

  Log('shell_summary:')
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

  # Just show osh-ovm because we know from the 'baseline' benchmark that it
  # uses significantly less than osh-cpython.
  vm %>%
    left_join(distinct_shells, by = c('shell_name', 'shell_hash')) %>%
    select(-c(shell_name, shell_hash)) %>%
    filter(shell_label == 'osh-ovm') %>%
    select(-c(shell_label)) %>%
    spread(key = metric_name, value = metric_value) %>%
    left_join(lines_by_filename, by = c('filename')) %>%
    arrange(host, num_lines) %>%
    mutate(filename_HREF = sourceUrl2(filename)) %>% 
    select(c(host, VmPeak, VmRSS, num_lines, filename, filename_HREF)) ->
    vm_table

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

  raw_data_table = data_frame(
    filename = basename(as.character(raw_data$path)),
    filename_HREF = benchmarkDataLink('osh-parser', filename, '')
  )
  print(raw_data_table)

  writeCsv(host_table, file.path(out_dir, 'hosts'))
  writeCsv(shell_table, file.path(out_dir, 'shells'))
  writeCsv(raw_data_table, file.path(out_dir, 'raw-data'))
  writeCsv(shell_summary, file.path(out_dir, 'summary'))
  writeCsv(elapsed, file.path(out_dir, 'elapsed'))
  writeCsv(rate, file.path(out_dir, 'rate'))

  writeCsv(vm_table, file.path(out_dir, 'virtual-memory'))

  Log('Wrote %s', out_dir)
}

RuntimeReport = function(in_dir, out_dir) {
  times = read.csv(file.path(in_dir, 'times.csv'))

  print(summary(times))
  print(head(times))

  #lines = read.csv(file.path(in_dir, 'lines.csv'))
  #raw_data = read.csv(file.path(in_dir, 'raw-data.csv'))
  #vm = read.csv(file.path(in_dir, 'virtual-memory.csv'))

  #writeCsv(host_table, file.path(out_dir, 'hosts'))
  Log('Wrote %s', out_dir)
}

main = function(argv) {
  action = argv[[1]]
  in_dir = argv[[2]]
  out_dir = argv[[3]]
  if (action == 'osh-parser') {
    ParserReport(in_dir, out_dir)
  } else if (action == 'osh-runtime') {
    RuntimeReport(in_dir, out_dir)
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
