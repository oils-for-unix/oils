#!/usr/bin/Rscript
#
# benchmarks/report.R -- Analyze data collected by shell scripts.
#
# Usage:
#   benchmarks/report.R OUT_DIR [TIMES_CSV...]

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

mycppUrl = function(path) {
  sprintf('https://github.com/oilshell/oil/blob/master/mycpp/examples/%s.py', path)
}


# TODO: Set up cgit because Github links are slow.
benchmarkDataLink = function(subdir, name, suffix) {
  #sprintf('../../../../benchmark-data/shell-id/%s', shell_id)
  sprintf('https://github.com/oilshell/benchmark-data/blob/master/%s/%s%s',
          subdir, name, suffix)
}

provenanceLink = function(subdir, name, suffix) {
  sprintf('../provenance/%s/%s%s', subdir, name, suffix)
}


GetOshLabel = function(shell_hash, num_hosts) {
  ### Given a string, return another string.

  if (num_hosts == 1) {
    prov_dir = '_tmp/provenance'
  } else {
    prov_dir = '../benchmark-data/'
  }
  path = sprintf('%s/shell-id/osh-%s/osh-version.txt', prov_dir, shell_hash)

  if (file.exists(path)) {
    Log('Reading %s', path)
    lines = readLines(path)
    if (length(grep('OVM', lines)) > 0) {
      label = 'osh-ovm'
    } else if (length(grep('CPython', lines)) > 0) {
      label = 'osh-cpython'
    } else {
      stop("Couldn't find OVM or CPython in the version string")
    }
  } else {
    stop(sprintf("%s doesn't exist", path))
  }
  return(label)
}

ShellLabels = function(shell_name, shell_hash, num_hosts) {
  ### Given 2 vectors, return a vector of readable labels.

  #Log('name %s', shell_name)
  #Log('hash  %s', shell_hash)

  labels = c()
  for (i in 1:length(shell_name)) {
    if (shell_name[i] == 'osh') {
      label = GetOshLabel(shell_hash[i], num_hosts)
    } else if (shell_name[i] == 'osh_eval.stripped') {
      label = 'oil-native'
    } else if (shell_name[i] == '_bin/cxx-opt/osh_eval.stripped') {
      label = 'opt/osh_eval'
    } else if (shell_name[i] == '_bin/cxx-bumpleak/osh_eval') {
      label = 'bumpleak/osh_eval'
    } else {
      label = shell_name[i]
    }
    Log('[%s] [%s]', shell_name[i], label)
    labels = c(labels, label)
  }

  return(labels)
}

DistinctHosts = function(t) {
  t %>% distinct(host_name, host_hash) -> distinct_hosts
  # The label is just the name
  distinct_hosts$host_label = distinct_hosts$host_name
  return(distinct_hosts)
}

DistinctShells = function(t) {
  t %>% distinct(shell_name, shell_hash) -> distinct_shells

  Log('')
  Log('Labeling shells')

  distinct_shells$shell_label = ShellLabels(distinct_shells$shell_name,
                                            distinct_shells$shell_hash,
                                            nrow(DistinctHosts(t)))
  return(distinct_shells)
}

ParserReport = function(in_dir, out_dir) {
  times = read.csv(file.path(in_dir, 'times.csv'))
  lines = read.csv(file.path(in_dir, 'lines.csv'))
  raw_data = read.csv(file.path(in_dir, 'raw-data.csv'))

  cachegrind = readTsv(file.path(in_dir, 'cachegrind.tsv'))

  # For joining by filename
  lines_by_filename = tibble(
      num_lines = lines$num_lines,
      filename = basename(lines$path)
  )

  # Remove failures
  times %>% filter(status == 0) %>% select(-c(status)) -> times
  cachegrind %>% filter(status == 0) %>% select(-c(status)) -> cachegrind

  # Add the number of lines, joining on path, and compute lines/sec
  # TODO: Is there a better way compute lines_per_ms and then drop
  # lines_per_sec?
  times %>%
    left_join(lines, by = c('path')) %>%
    mutate(filename = basename(path), filename_HREF = sourceUrl(path),
           max_rss_MB = max_rss_KiB * 1024 / 1e6,
           elapsed_ms = elapsed_secs * 1000,
           user_ms = user_secs * 1000,
           sys_ms = sys_secs * 1000,
           lines_per_ms = num_lines / elapsed_ms) %>%
    select(-c(path, max_rss_KiB, elapsed_secs, user_secs, sys_secs)) ->
    joined_times

  #print(head(times))
  #print(head(lines))
  #print(head(vm))
  #print(head(joined_times))

  print(summary(joined_times))

  #
  # Find distinct shells and hosts, and label them for readability.
  #

  distinct_hosts = DistinctHosts(joined_times)
  Log('')
  Log('Distinct hosts')
  print(distinct_hosts)

  distinct_shells = DistinctShells(joined_times)
  Log('')
  Log('Distinct shells')
  print(distinct_shells)

  # Replace name/hash combinations with labels.
  joined_times %>%
    left_join(distinct_hosts, by = c('host_name', 'host_hash')) %>%
    left_join(distinct_shells, by = c('shell_name', 'shell_hash')) %>%
    select(-c(host_name, host_hash, shell_name, shell_hash)) ->
    joined_times

  # Like 'times', but do shell_label as one step
  distinct_shells_2 = DistinctShells(cachegrind)
  cachegrind %>%
    left_join(lines, by = c('path')) %>%
    select(-c(elapsed_secs, user_secs, sys_secs, max_rss_KiB)) %>% 
    left_join(distinct_shells_2, by = c('shell_name', 'shell_hash')) %>%
    select(-c(shell_name, shell_hash)) ->
    joined_cachegrind

  Log('summary(joined_times):')
  print(summary(joined_times))
  Log('head(joined_times):')
  print(head(joined_times))

  # Summarize rates by platform/shell
  joined_times %>%
    mutate(host_label = paste("host", host_label)) %>%
    group_by(host_label, shell_label) %>%
    summarize(total_lines = sum(num_lines), total_ms = sum(elapsed_ms)) %>%
    mutate(lines_per_ms = total_lines / total_ms) %>%
    select(-c(total_ms)) %>%
    spread(key = host_label, value = lines_per_ms) ->
    times_summary

  # Sort by parsing rate on the fast machine
  if ("host lenny" %in% colnames(times_summary)) {
    times_summary %>% arrange(desc(`host lenny`)) -> times_summary
  } else {
    times_summary %>% arrange(desc(`host no-host`)) -> times_summary
  }

  Log('times_summary:')
  print(times_summary)

  # Summarize cachegrind by platform/shell
  # Bug fix: as.numeric(irefs) avoids 32-bit integer overflow!
  joined_cachegrind %>%
    group_by(shell_label) %>%
    summarize(total_lines = sum(num_lines), total_irefs = sum(as.numeric(irefs))) %>%
    mutate(thousand_irefs_per_line = total_irefs / total_lines / 1000) %>%
    select(-c(total_irefs)) ->
    cachegrind_summary

  if ("no-host" %in% distinct_hosts$host_label) {

    # We don't have all the shells
    elapsed = NA
    rate = NA
    max_rss = NA
    instructions = NA

    joined_times %>%
      select(c(shell_label, elapsed_ms, user_ms, sys_ms, max_rss_MB,
               num_lines, filename, filename_HREF)) %>%
      arrange(filename, elapsed_ms) -> times_flat

  } else {

    times_flat = NA

    # Elapsed seconds for each shell by platform and file
    joined_times %>%
      select(-c(lines_per_ms, user_ms, sys_ms, max_rss_MB)) %>% 
      spread(key = shell_label, value = elapsed_ms) %>%
      arrange(host_label, num_lines) %>%
      mutate(osh_to_bash_ratio = `oil-native` / bash) %>% 
      select(c(host_label, bash, dash, mksh, zsh,
               `osh-ovm`, `osh-cpython`, `oil-native`,
               osh_to_bash_ratio, num_lines, filename, filename_HREF)) ->
      elapsed

    Log('\n')
    Log('ELAPSED')
    print(elapsed)

    # Rates by file and shell
    joined_times  %>%
      select(-c(elapsed_ms, user_ms, sys_ms, max_rss_MB)) %>% 
      spread(key = shell_label, value = lines_per_ms) %>%
      arrange(host_label, num_lines) %>%
      select(c(host_label, bash, dash, mksh, zsh,
               `osh-ovm`, `osh-cpython`, `oil-native`,
               num_lines, filename, filename_HREF)) ->
      rate

    Log('\n')
    Log('RATE')
    print(rate)

    # Memory usage by file
    joined_times %>%
      select(-c(elapsed_ms, lines_per_ms, user_ms, sys_ms)) %>% 
      spread(key = shell_label, value = max_rss_MB) %>%
      arrange(host_label, num_lines) %>%
      select(c(host_label, bash, dash, mksh, zsh,
               `osh-ovm`, `osh-cpython`, `oil-native`,
               num_lines, filename, filename_HREF)) ->
      max_rss

    Log('\n')
    Log('joined_cachegrind has %d rows', nrow(joined_cachegrind))
    #print(joined_cachegrind)
    print(joined_cachegrind %>% filter(path == 'benchmarks/testdata/configure-helper.sh'))

    # Cachegrind instructions by file
    joined_cachegrind %>%
      mutate(thousand_irefs_per_line = irefs / num_lines / 1000) %>%
      select(-c(irefs)) %>%
      spread(key = shell_label, value = thousand_irefs_per_line) %>%
      arrange(num_lines) %>%
      mutate(filename = basename(path), filename_HREF = sourceUrl(path)) %>% 
      select(c(bash, dash, mksh, `oil-native`,
               num_lines, filename, filename_HREF)) ->
      instructions

    Log('\n')
    Log('instructions has %d rows', nrow(instructions))
    print(instructions)
  }

  WriteProvenance(distinct_hosts, distinct_shells, out_dir)

  raw_data_table = tibble(
    filename = basename(as.character(raw_data$path)),
    filename_HREF = benchmarkDataLink('osh-parser', filename, '')
  )
  #print(raw_data_table)

  writeCsv(raw_data_table, file.path(out_dir, 'raw-data'))

  precision = ColumnPrecision(list(total_ms = 0))  # round to nearest millisecond
  writeCsv(times_summary, file.path(out_dir, 'summary'), precision)

  precision = ColumnPrecision(list(), default = 1)
  writeTsv(cachegrind_summary, file.path(out_dir, 'cachegrind_summary'), precision)

  if (!is.na(times_flat)) {
    writeTsv(times_flat, file.path(out_dir, 'times_flat'), precision)
  }

  if (!is.na(elapsed)) {  # equivalent to no-host
    # Round to nearest millisecond, but the ratio has a decimal point.
    precision = ColumnPrecision(list(osh_to_bash_ratio = 1), default = 0)

    writeCsv(elapsed, file.path(out_dir, 'elapsed'), precision)
    writeCsv(rate, file.path(out_dir, 'rate'))
    writeCsv(max_rss, file.path(out_dir, 'max_rss'))

    precision = ColumnPrecision(list(), default = 1)
    writeTsv(instructions, file.path(out_dir, 'instructions'), precision)
  }

  Log('Wrote %s', out_dir)
}

WriteProvenance = function(distinct_hosts, distinct_shells, out_dir, tsv = F) {

  num_hosts = nrow(distinct_hosts)
  if (num_hosts == 1) {
    linkify = provenanceLink
  } else {
    linkify = benchmarkDataLink
  }

  # Should be:
  # host_id_url
  # And then csv_to_html will be smart enough?  It should take --url flag?
  host_table = tibble(
    host_label = distinct_hosts$host_label,
    host_id = paste(distinct_hosts$host_name,
                    distinct_hosts$host_hash, sep='-'),
    host_id_HREF = linkify('host-id', host_id, '/')
  )
  Log('host_table')
  print(host_table)
  Log('')

  shell_table = tibble(
    shell_label = distinct_shells$shell_label,
    shell_id = paste(distinct_shells$shell_name,
                     distinct_shells$shell_hash, sep='-'),
    shell_id_HREF = linkify('shell-id', shell_id, '/')
  )
  Log('distinct_shells')
  print(distinct_shells)
  Log('')

  Log('shell_table')
  print(shell_table)
  Log('')

  if (tsv) {
    writeTsv(host_table, file.path(out_dir, 'hosts'))
    writeTsv(shell_table, file.path(out_dir, 'shells'))
  } else {
    writeCsv(host_table, file.path(out_dir, 'hosts'))
    writeCsv(shell_table, file.path(out_dir, 'shells'))
  }
}

RuntimeReport = function(in_dir, out_dir) {
  times = read.csv(file.path(in_dir, 'times.csv'))

  times %>% filter(status != 0) -> failed
  if (nrow(failed) != 0) {
    print(failed)
    stop('Some osh-runtime tasks failed')
  }

  distinct_hosts = DistinctHosts(times)
  distinct_shells = DistinctShells(times)

  print(distinct_hosts)
  Log('')
  print(distinct_shells)
  Log('')

  #return()

  # Replace name/hash combinations with labels.
  times %>%
    left_join(distinct_hosts, by = c('host_name', 'host_hash')) %>%
    left_join(distinct_shells, by = c('shell_name', 'shell_hash')) %>%
    select(-c(host_name, host_hash, shell_name, shell_hash)) ->
    details

  #Log('times')
  #print(times)

  Log('details')
  print(details)

  # Sort by osh elapsed ms.
  details %>%
    mutate(elapsed_ms = elapsed_secs * 1000,
           task_arg = basename(task_arg)) %>%
    select(-c(status, elapsed_secs, user_secs, sys_secs, max_rss_KiB)) %>%
    spread(key = shell_label, value = elapsed_ms) %>%
    mutate(py_bash_ratio = `osh-cpython` / bash) %>%
    mutate(native_bash_ratio = `oil-native` / bash) %>%
    arrange(task_arg, host_label) %>%
    select(c(task_arg, host_label, bash, dash, `osh-cpython`, `oil-native`, py_bash_ratio, native_bash_ratio)) ->
    elapsed

  Log('elapsed')
  print(elapsed)

  #print(summary(elapsed))
  #print(head(elapsed))

  details %>%
    mutate(max_rss_MB = max_rss_KiB * 1024 / 1e6,
           task_arg = basename(task_arg)) %>%
    select(-c(status, elapsed_secs, user_secs, sys_secs, max_rss_KiB)) %>%
    spread(key = shell_label, value = max_rss_MB) %>%
    mutate(py_bash_ratio = `osh-cpython` / bash) %>%
    mutate(native_bash_ratio = `oil-native` / bash) %>%
    arrange(task_arg, host_label) %>%
    select(c(task_arg, host_label, bash, dash, `osh-cpython`, `oil-native`, py_bash_ratio, native_bash_ratio)) ->
    max_rss

  print(summary(elapsed))
  print(head(elapsed))

  WriteProvenance(distinct_hosts, distinct_shells, out_dir)

  precision = ColumnPrecision(list(bash = 0, dash = 0, `osh-cpython` = 0, `oil-native` = 0))
  writeCsv(elapsed, file.path(out_dir, 'elapsed'), precision)
  writeCsv(max_rss, file.path(out_dir, 'max_rss'))

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

  # Not using DistinctHosts() because field host_hash isn't collected
  num_hosts = nrow(vm %>% distinct(host))

  vm %>%
    rename(kib = metric_value) %>%
    mutate(shell_label = ShellLabels(shell_name, shell_hash, num_hosts),
           megabytes = kib * 1024 / 1e6) %>%
    select(-c(shell_name, kib)) %>%
    spread(key = c(metric_name), value = megabytes) %>%
    rename(VmPeak_MB = VmPeak, VmRSS_MB = VmRSS) %>%
    select(c(shell_label, shell_hash, host, VmRSS_MB, VmPeak_MB)) %>%
    arrange(shell_label, shell_hash, host, VmPeak_MB) ->
    vm

  print(vm)

  writeCsv(vm, file.path(out_dir, 'vm-baseline'))
}

WriteOvmBuildDetails = function(distinct_hosts, distinct_compilers, out_dir) {
  host_table = tibble(
    host_label = distinct_hosts$host_label,
    host_id = paste(distinct_hosts$host_name,
                    distinct_hosts$host_hash, sep='-'),
    host_id_HREF = benchmarkDataLink('host-id', host_id, '/')
  )
  print(host_table)

  dc = distinct_compilers
  compiler_table = tibble(
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
    mutate(src_dir = basename(src_dir),
           host_label = paste("host ", host_label),
           is_conf = str_detect(action, 'configure'),
           is_ovm = str_detect(action, 'oil.ovm'),
           is_dbg = str_detect(action, 'dbg'),
           ) %>%
    select(host_label, src_dir, compiler_label, action, is_conf, is_ovm, is_dbg,
           elapsed_secs) %>%
    spread(key = c(host_label), value = elapsed_secs) %>%
    arrange(src_dir, compiler_label, desc(is_conf), is_ovm, desc(is_dbg)) %>%
    select(-c(is_conf, is_ovm, is_dbg)) ->
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

  # paths look like _tmp/ovm-build/bin/clang/osh_eval.stripped
  native_sizes %>%
    select(c(host_label, path, num_bytes)) %>%
    mutate(host_label = paste("host ", host_label),
           binary = basename(path),
           compiler = basename(dirname(path)),
           ) %>%
    select(-c(path)) %>%
    spread(key = c(host_label), value = num_bytes) %>%
    arrange(compiler, binary) ->
    native_sizes

  # NOTE: These don't have the host and compiler.
  writeTsv(times, file.path(out_dir, 'times'))
  writeTsv(bytecode_size, file.path(out_dir, 'bytecode-size'))
  writeTsv(sizes, file.path(out_dir, 'sizes'))
  writeTsv(native_sizes, file.path(out_dir, 'native-sizes'))

  # TODO: I want a size report too
  #writeCsv(sizes, file.path(out_dir, 'sizes'))
}

unique_stdout_md5sum = function(t, num_expected) {
  u = n_distinct(t$stdout_md5sum)
  if (u != num_expected) {
    t %>% select(c(host_name, task_name, arg1, arg2, runtime_name, stdout_md5sum)) %>% print()
    stop(sprintf('Expected %d unique md5sums, got %d', num_expected, u))
  }
}

ComputeReport = function(in_dir, out_dir) {
  # TSV file, not CSV
  times = read.table(file.path(in_dir, 'times.tsv'), header=T)
  print(times)

  times %>% filter(status != 0) -> failed
  if (nrow(failed) != 0) {
    print(failed)
    stop('Some compute tasks failed')
  }

  #
  # Check correctness
  #

  times %>% filter(task_name == 'hello') %>% unique_stdout_md5sum(1)
  times %>% filter(task_name == 'fib') %>% unique_stdout_md5sum(1)
  times %>% filter(task_name == 'word_freq') %>% unique_stdout_md5sum(1)
  # 3 different inputs
  times %>% filter(task_name == 'parse_help') %>% unique_stdout_md5sum(3)

  times %>% filter(task_name == 'bubble_sort') %>% unique_stdout_md5sum(2)

  # TODO: 
  # - osh_eval doesn't implement unicode LANG=C
  # - bash behaves differently on your desktop vs. in the container
  #   - might need layer-locales in the image?

  #times %>% filter(task_name == 'palindrome' & arg1 == 'unicode') %>% unique_stdout_md5sum(1)
  # Ditto here
  #times %>% filter(task_name == 'palindrome' & arg1 == 'bytes') %>% unique_stdout_md5sum(1)

  #
  # Find distinct shells and hosts, and label them for readability.
  #

  # Runtimes are called shells, as a hack for code reuse
  times %>%
    mutate(shell_name = runtime_name, shell_hash = runtime_hash) %>%
    select(c(host_name, host_hash, shell_name, shell_hash)) ->
    tmp

  distinct_hosts = DistinctHosts(tmp)
  Log('')
  Log('Distinct hosts')
  print(distinct_hosts)

  distinct_shells = DistinctShells(tmp)
  Log('')
  Log('Distinct runtimes')
  print(distinct_shells)

  num_hosts = nrow(distinct_hosts)

  times %>%
    select(-c(status, stdout_md5sum, host_hash, runtime_hash)) %>%
    mutate(runtime_label = ShellLabels(runtime_name, runtime_hash, num_hosts),
           elapsed_ms = elapsed_secs * 1000,
           user_ms = user_secs * 1000,
           sys_ms = sys_secs * 1000,
           max_rss_MB = max_rss_KiB * 1024 / 1e6) %>%
    select(-c(runtime_name, elapsed_secs, user_secs, sys_secs, max_rss_KiB)) %>%
    arrange(host_name, task_name, arg1, arg2, user_ms) ->
    details

  details %>% filter(task_name == 'hello') %>% select(-c(task_name)) -> hello
  details %>% filter(task_name == 'fib') %>% select(-c(task_name)) -> fib
  details %>% filter(task_name == 'word_freq') %>% select(-c(task_name)) -> word_freq
  # There's no arg2
  details %>% filter(task_name == 'parse_help') %>% select(-c(task_name, arg2)) -> parse_help

  details %>% filter(task_name == 'bubble_sort') %>% select(-c(task_name)) -> bubble_sort
  details %>% filter(task_name == 'palindrome' & arg1 == 'unicode') %>% select(-c(task_name)) -> palindrome

  writeTsv(details, file.path(out_dir, 'details'))

  writeTsv(hello, file.path(out_dir, 'hello'))
  writeTsv(fib, file.path(out_dir, 'fib'))
  writeTsv(word_freq, file.path(out_dir, 'word_freq'))
  writeTsv(parse_help, file.path(out_dir, 'parse_help'))

  writeTsv(bubble_sort, file.path(out_dir, 'bubble_sort'))
  writeTsv(palindrome, file.path(out_dir, 'palindrome'))

  WriteProvenance(distinct_hosts, distinct_shells, out_dir, tsv = T)
}

GcReport = function(in_dir, out_dir) {
  parser_times = read.table(file.path(in_dir, 'parser.tsv'), header=T)

  parser_times %>% filter(status != 0) -> failed
  if (nrow(failed) != 0) {
    print(failed)
    stop('Some gc tasks failed')
  }

  parser_times %>%
    mutate(elapsed_ms = elapsed_secs * 1000,
           user_ms = user_secs * 1000,
           sys_ms = sys_secs * 1000,
           max_rss_MB = max_rss_KiB * 1024 / 1e6) %>%
    select(-c(status, elapsed_secs, user_secs, sys_secs, max_rss_KiB)) %>%
    select(c(elapsed_ms, user_ms, sys_ms, max_rss_MB, shell, comment)) ->
    parser_out

  writeTsv(parser_out, file.path(out_dir, 'parser'))
}

MyCppReport = function(in_dir, out_dir) {
  # TSV file, not CSV
  times = read.table(file.path(in_dir, 'benchmark-table.tsv'), header=T)
  print(times)

  times %>% filter(status != 0) -> failed
  if (nrow(failed) != 0) {
    print(failed)
    stop('Some mycpp tasks failed')
  }

  # Don't care about elapsed and system
  times %>% select(-c(status, elapsed_secs, sys_secs, bin, task_out)) %>%
    mutate(example_name_HREF = mycppUrl(example_name),
           user_ms = user_secs * 1000, 
           max_rss_MB = max_rss_KiB * 1024 / 1e6) %>%
    select(-c(user_secs, max_rss_KiB)) ->
    details

  details %>% select(-c(max_rss_MB)) %>%
    spread(key = impl, value = user_ms) %>%
    mutate(`C++ : Python` = `C++` / Python) %>%
    arrange(`C++ : Python`) ->
    user_time

  details %>% select(-c(user_ms)) %>%
    spread(key = impl, value = max_rss_MB) %>%
    mutate(`C++ : Python` = `C++` / Python) %>%
    arrange(`C++ : Python`) ->
    max_rss

  # Sometimes it speeds up by more than 10x
  precision3 = ColumnPrecision(list(`C++ : Python` = 3))
  precision2 = ColumnPrecision(list(`C++ : Python` = 2))

  writeTsv(user_time, file.path(out_dir, 'user_time'), precision3)
  writeTsv(max_rss, file.path(out_dir, 'max_rss'), precision2)
  writeTsv(details, file.path(out_dir, 'details'))
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

  } else if (action == 'compute') {
    ComputeReport(in_dir, out_dir)

  } else if (action == 'gc') {
    GcReport(in_dir, out_dir)

  } else if (action == 'mycpp') {
    MyCppReport(in_dir, out_dir)

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
