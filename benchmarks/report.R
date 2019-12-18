#!/usr/bin/Rscript
#
# benchmarks/report.R -- Analyze data collected by shell scripts.
#
# Usage:
#   osh-parser.R OUT_DIR [TIMES_CSV...]

library(dplyr)
library(tidyr)  # spread()
library(stringr)

source('benchmarks/common.R')

options(stringsAsFactors = F)

sourceUrl = function(path) {
  sprintf('https://github.com/oilshell/oil/blob/master/%s', path)
}

# Takes a filename, not a path.
sourceUrl2 = function(filename) {
  sprintf(
      'https://github.com/oilshell/oil/blob/master/benchmarks/testdata/%s',
      filename)
}

# TODO: Set up cgit because Github links are slow.
benchmarkDataLink = function(subdir, name, suffix) {
  #sprintf('../../../../benchmark-data/shell-id/%s', shell_id)
  sprintf('https://github.com/oilshell/benchmark-data/blob/master/%s/%s%s',
          subdir, name, suffix)
}

GetOshLabel = function(shell_hash) {
  path = sprintf('../benchmark-data/shell-id/osh-%s/osh-version.txt',
                 shell_hash)
  Log('Reading %s', path)
  lines = readLines(path)
  if (length(grep('OVM', lines)) > 0) {
    label = 'osh-ovm'
  } else if (length(grep('CPython', lines)) > 0) {
    label = 'osh-cpython'
  } else {
    stop("Couldn't find OVM or CPython in the version string")
  }
  return( label)
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
      label = GetOshLabel(row$shell_hash)
    } else if (row$shell_name == 'osh_parse.opt.stripped') {
      label = 'osh-native'
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
    mutate(host_label = paste("host", host_label)) %>%
    group_by(host_label, shell_label) %>%
    summarize(total_lines = sum(num_lines), total_ms = sum(elapsed_ms)) %>%
    mutate(lines_per_ms = total_lines / total_ms) %>%
    select(-c(total_ms)) %>%
    spread(key = host_label, value = lines_per_ms) %>%
    # sort by parsing rate on the fast machine
    arrange(desc(`host lisa`)) ->
    shell_summary

  Log('shell_summary:')
  print(shell_summary)

  # Elapsed seconds for each shell by platform and file
  all_times %>%
    select(-c(lines_per_ms)) %>% 
    spread(key = shell_label, value = elapsed_ms) %>%
    arrange(host_label, num_lines) %>%
    mutate(filename = basename(path), filename_HREF = sourceUrl(path),
           osh_to_bash_ratio = `osh-native` / bash) %>% 
    select(c(host_label, bash, dash, mksh, zsh,
             `osh-ovm`, `osh-cpython`, `osh-native`,
             osh_to_bash_ratio, num_lines, filename, filename_HREF)) ->
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
    select(c(host_label, bash, dash, mksh, zsh,
             `osh-ovm`, `osh-cpython`, `osh-native`,
             num_lines, filename, filename_HREF)) ->
    rate

  # Just show osh-ovm because we know from the 'baseline' benchmark that it
  # uses significantly less than osh-cpython.
  vm %>%
    left_join(distinct_shells, by = c('shell_name', 'shell_hash')) %>%
    select(-c(shell_name, shell_hash)) %>%
    filter(shell_label == 'osh-ovm') %>%
    select(-c(shell_label)) %>%
    rename(kib = metric_value) %>%
    mutate(megabytes = kib * 1024 / 1e6) %>%
    select(-c(kib)) %>%
    spread(key = metric_name, value = megabytes) %>%
    left_join(lines_by_filename, by = c('filename')) %>%
    arrange(num_lines, host) %>%
    mutate(filename_HREF = sourceUrl2(filename)) %>% 
    rename(VmPeak_MB = VmPeak, VmRSS_MB = VmRSS) %>%
    select(c(host, VmRSS_MB, VmPeak_MB, num_lines, filename, filename_HREF)) ->
    vm_table

  Log('\n')
  Log('RATE')
  print(rate)

  WriteDetails(distinct_hosts, distinct_shells, out_dir)

  raw_data_table = data_frame(
    filename = basename(as.character(raw_data$path)),
    filename_HREF = benchmarkDataLink('osh-parser', filename, '')
  )
  print(raw_data_table)

  writeCsv(raw_data_table, file.path(out_dir, 'raw-data'))

  precision = ColumnPrecision(list(total_ms = 0))  # round to nearest millisecond
  writeCsv(shell_summary, file.path(out_dir, 'summary'), precision)

  # Round to nearest millisecond, but the ratio has a decimal point.
  precision = ColumnPrecision(list(osh_to_bash_ratio = 1), default = 0)
  writeCsv(elapsed, file.path(out_dir, 'elapsed'), precision)
  writeCsv(rate, file.path(out_dir, 'rate'))

  writeCsv(vm_table, file.path(out_dir, 'virtual-memory'))

  Log('Wrote %s', out_dir)
}

WriteDetails = function(distinct_hosts, distinct_shells, out_dir) {
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

  writeCsv(host_table, file.path(out_dir, 'hosts'))
  writeCsv(shell_table, file.path(out_dir, 'shells'))
}

RuntimeReport = function(in_dir, out_dir) {
  times = read.csv(file.path(in_dir, 'times.csv'))
  vm = read.csv(file.path(in_dir, 'virtual-memory.csv'))

  times %>% filter(status != 0) -> failed
  if (nrow(failed) != 0) {
    print(failed)
    stop('Some osh-runtime tasks failed')
  }

  # Host label is the same as name
  times %>% distinct(host_name, host_hash) -> distinct_hosts
  distinct_hosts$host_label = distinct_hosts$host_name
  print(distinct_hosts)

  # Shell label is the same as name.  We only have one OSH build.
  times %>% distinct(shell_name, shell_hash) -> distinct_shells
  distinct_shells$shell_label = distinct_shells$shell_name
  print(distinct_shells)

  # Replace name/hash combinations with labels.
  times %>%
    left_join(distinct_hosts, by = c('host_name', 'host_hash')) %>%
    left_join(distinct_shells, by = c('shell_name', 'shell_hash')) %>%
    select(-c(host_name, host_hash, shell_name, shell_hash)) ->
    times

  print(times)

  # Sort by osh elapsed ms.
  times %>%
    mutate(elapsed_ms = elapsed_secs * 1000,
           task_arg = basename(task_arg)) %>%
    select(-c(status, elapsed_secs)) %>%
    spread(key = shell_label, value = elapsed_ms) %>%
    mutate(osh_to_bash_ratio = osh / bash) %>%
    arrange(task_arg, host_label) %>%
    select(c(task_arg, host_label, bash, dash, osh, osh_to_bash_ratio)) ->
    times

  print(summary(times))
  print(head(times))

  Log('VM:')
  print(vm)

  # This is a separate analysis.  We record virtual memory for both the parser
  # and runtime.  The parser takes all the memory, which is not too surprising.
  vm %>%
    filter(shell_name == 'osh') %>%
    select(-c(shell_name, shell_hash)) %>%
    rename(kib = metric_value) %>%
    mutate(megabytes = kib * 1024 / 1e6) %>%
    select(-c(kib)) %>%
    mutate(mem_name = paste(event, metric_name, 'MB', sep = '_')) %>%
    select(-c(event, metric_name)) %>%
    spread(key = c(mem_name), value = megabytes) %>%
    arrange(task_arg, host) %>%
    select(c(task_arg, host, runtime_VmRSS_MB, runtime_VmPeak_MB)) ->
    vm

  Log('VM:')
  print(vm)

  WriteDetails(distinct_hosts, distinct_shells, out_dir)

  precision = ColumnPrecision(list(bash = 0, dash = 0, osh = 0))
  writeCsv(times, file.path(out_dir, 'times'), precision)
  writeCsv(vm, file.path(out_dir, 'virtual-memory'))

  Log('Wrote %s', out_dir)
}

# foo/bar/name.sh__oheap -> name.sh
filenameFromPath = function(path) {
  # https://stackoverflow.com/questions/33683862/first-entry-from-string-split
  # Not sure why [[1]] doesn't work?
  parts = strsplit(basename(path), '__', fixed = T)
  sapply(parts, head, 1)
}

OheapReport = function(in_dir, out_dir) {
  sizes = read.csv(file.path(in_dir, 'sizes.csv'))

  sizes %>%
    mutate(filename = filenameFromPath(path),
           metric_name = paste(format, compression, sep = '_'),
           kilobytes = num_bytes / 1000) %>%
    select(-c(path, format, compression, num_bytes)) %>%
    spread(key = c(metric_name), value = kilobytes) %>%
    select(c(text_none, text_gz, text_xz, oheap_none, oheap_gz, oheap_xz, filename)) %>%
    arrange(text_none) ->
    sizes
  print(sizes)

  # Interesting:
  # - oheap is 2-7x bigger uncompressed, and 4-12x bigger compressed.
  # - oheap is less compressible than text!

  # TODO: The ratio needs 2 digits of precision.

  sizes %>%
    transmute(oheap_to_text = oheap_none / text_none,
              xz_text = text_xz / text_none,
              xz_oheap = oheap_xz / oheap_none,
              oheap_to_text_xz = oheap_xz / text_xz,
              ) ->
    ratios

  print(ratios)

  precision = SamePrecision(0)
  writeCsv(sizes, file.path(out_dir, 'encoding_size'), precision)
  precision = SamePrecision(2)
  writeCsv(ratios, file.path(out_dir, 'encoding_ratios'), precision)

  Log('Wrote %s', out_dir)
}

VmBaselineReport = function(in_dir, out_dir) {
  vm = read.csv(file.path(in_dir, 'vm-baseline.csv'))
  #print(vm)

  # TODO: Should label osh-ovm and osh-cpython, like above.

  vm %>%
    rename(kib = metric_value) %>%
    mutate(megabytes = kib * 1024 / 1e6) %>%
    select(-c(kib)) %>%
    spread(key = c(metric_name), value = megabytes) %>%
    rename(VmPeak_MB = VmPeak, VmRSS_MB = VmRSS) %>%
    select(c(shell_name, shell_hash, host, VmRSS_MB, VmPeak_MB)) %>%
    arrange(shell_name, shell_hash, host, VmPeak_MB) ->
    vm

  print(vm)

  writeCsv(vm, file.path(out_dir, 'vm-baseline'))
}

WriteOvmBuildDetails = function(distinct_hosts, distinct_compilers, out_dir) {
  host_table = data_frame(
    host_label = distinct_hosts$host_label,
    host_id = paste(distinct_hosts$host_name,
                    distinct_hosts$host_hash, sep='-'),
    host_id_HREF = benchmarkDataLink('host-id', host_id, '/')
  )
  print(host_table)

  dc = distinct_compilers
  compiler_table = data_frame(
    compiler_label = dc$compiler_label,
    compiler_id = paste(dc$compiler_label, dc$compiler_hash, sep='-'),
    compiler_id_HREF = benchmarkDataLink('compiler-id', compiler_id, '/')
  )
  print(compiler_table)

  writeTsv(host_table, file.path(out_dir, 'hosts'))
  writeTsv(compiler_table, file.path(out_dir, 'compilers'))
}

OvmBuildReport = function(in_dir, out_dir) {
  times = readTsv(file.path(in_dir, 'times.tsv'))
  bytecode_size = readTsv(file.path(in_dir, 'bytecode-size.tsv'))
  bin_sizes = readTsv(file.path(in_dir, 'bin-sizes.tsv'))
  native_sizes = readTsv(file.path(in_dir, 'native-sizes.tsv'))
  raw_data = readTsv(file.path(in_dir, 'raw-data.tsv'))

  times %>% filter(status != 0) -> failed
  if (nrow(failed) != 0) {
    print(failed)
    stop('Some ovm-build tasks failed')
  }

  times %>% distinct(host_name, host_hash) -> distinct_hosts
  distinct_hosts$host_label = distinct_hosts$host_name

  times %>% distinct(compiler_path, compiler_hash) -> distinct_compilers
  distinct_compilers$compiler_label = basename(distinct_compilers$compiler_path)

  #print(distinct_hosts)
  #print(distinct_compilers)

  WriteOvmBuildDetails(distinct_hosts, distinct_compilers, out_dir)

  times %>%
    select(-c(status)) %>%
    left_join(distinct_hosts, by = c('host_name', 'host_hash')) %>%
    left_join(distinct_compilers, by = c('compiler_path', 'compiler_hash')) %>%
    select(-c(host_name, host_hash, compiler_path, compiler_hash)) %>%
    mutate(src_dir = basename(src_dir)) %>%
    arrange(host_label, src_dir) %>%
    select(host_label, compiler_label, src_dir, action, elapsed_secs) %>%
    mutate(host_label = paste("host ", host_label)) %>%
    spread(key = c(host_label), value = elapsed_secs) ->
    times

  #print(times)

  bytecode_size %>%
    rename(bytecode_size = num_bytes) %>%
    select(-c(path)) ->
    bytecode_size

  bin_sizes %>%
    # reorder
    select(c(host_label, path, num_bytes)) %>%
    left_join(bytecode_size, by = c('host_label')) %>%
    mutate(native_code_size = num_bytes - bytecode_size) ->
    sizes

    #mutate(path = basename(path)) %>%
  native_sizes %>%
    select(c(host_label, path, num_bytes)) ->
    native_sizes

  # NOTE: These don't have the host and compiler.
  writeTsv(times, file.path(out_dir, 'times'))
  writeTsv(bytecode_size, file.path(out_dir, 'bytecode-size'))
  writeTsv(sizes, file.path(out_dir, 'sizes'))
  writeTsv(native_sizes, file.path(out_dir, 'native-sizes'))

  # TODO: I want a size report too
  #writeCsv(sizes, file.path(out_dir, 'sizes'))
}

main = function(argv) {
  action = argv[[1]]
  in_dir = argv[[2]]
  out_dir = argv[[3]]

  if (action == 'osh-parser') {
    ParserReport(in_dir, out_dir)

  } else if (action == 'osh-runtime') {
    RuntimeReport(in_dir, out_dir)

  } else if (action == 'vm-baseline') {
    VmBaselineReport(in_dir, out_dir)

  } else if (action == 'ovm-build') {
    OvmBuildReport(in_dir, out_dir)

  } else if (action == 'oheap') {
    OheapReport(in_dir, out_dir)

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
