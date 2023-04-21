#!/usr/bin/env Rscript
#
# benchmarks/report.R -- Analyze data collected by shell scripts.
#
# Usage:
#   benchmarks/report.R OUT_DIR [TIMES_CSV...]

# Supress warnings about functions masked from 'package:stats' and 'package:base'
#   filter, lag
#   intersect, setdiff, setequal, union
library(dplyr, warn.conflicts = FALSE)
library(tidyr)  # spread()
library(stringr)

source('benchmarks/common.R')

options(stringsAsFactors = F)

# For pretty printing
commas = function(x) {
  format(x, big.mark=',')
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
  sprintf('../%s/%s%s', subdir, name, suffix)
}


GetOshLabel = function(shell_hash, prov_dir) {
  ### Given a string, return another string.

  path = sprintf('%s/shell-id/osh-%s/sh-path.txt', prov_dir, shell_hash)

  if (file.exists(path)) {
    Log('Reading %s', path)
    lines = readLines(path)
    if (length(grep('_bin/osh', lines)) > 0) {
      label = 'osh-ovm'
    } else if (length(grep('bin/osh', lines)) > 0) {
      label = 'osh-cpython'
    } else if (length(grep('_bin/.*/osh', lines)) > 0) {
      label = 'osh-native'
    } else {
      stop("Expected _bin/osh, bin/osh, or _bin/.*/osh")
    }
  } else {
    stop(sprintf("%s doesn't exist", path))
  }
  return(label)
}

opt_suffix1 = '_bin/cxx-opt/osh'
opt_suffix2 = '_bin/cxx-opt-sh/osh'

ShellLabels = function(shell_name, shell_hash, num_hosts) {
  ### Given 2 vectors, return a vector of readable labels.

  # TODO: Clean up callers.  Some metrics all this function with a
  # shell/runtime BASENAME, and others a PATH
  # - e.g. ComputeReport calls this with runtime_name which is actually a PATH

  #Log('name %s', shell_name)
  #Log('hash  %s', shell_hash)

  if (num_hosts == 1) {
    prov_dir = '_tmp'
  } else {
    prov_dir = '../benchmark-data/'
  }

  labels = c()
  for (i in 1:length(shell_name)) {
    sh = shell_name[i]
    if (sh == 'osh') {
      label = GetOshLabel(shell_hash[i], prov_dir)

    } else if (endsWith(sh, opt_suffix1) || endsWith(sh, opt_suffix2)) {
      label = 'opt/osh'

    } else if (endsWith(sh, '_bin/cxx-opt+bumpleak/osh')) {
      label = 'bumpleak/osh'

    } else {
      label = sh
    }

    Log('[%s] [%s]', shell_name[i], label)
    labels = c(labels, label)
  }

  return(labels)
}

# Simple version of the above, used by benchmarks/gc
ShellLabelFromPath = function(sh_path) {
  labels = c()
  for (i in 1:length(sh_path)) {
    sh = sh_path[i]

    if (endsWith(sh, opt_suffix1) || endsWith(sh, opt_suffix2)) {
      # the opt binary is osh-native
      label = 'osh-native'

    } else if (endsWith(sh, '_bin/cxx-opt+bumpleak/osh')) {
      label = 'bumpleak/osh'

    } else if (endsWith(sh, '_bin/osh')) {  # the app bundle
      label = 'osh-ovm'

    } else if (endsWith(sh, 'bin/osh')) {
      label = 'osh-cpython'

    } else {
      label = sh
    }
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

DistinctShells = function(t, num_hosts = -1) {
  t %>% distinct(shell_name, shell_hash) -> distinct_shells

  Log('')
  Log('Labeling shells')

  # Calculate it if not passed
  if (num_hosts == -1) {
    num_hosts = nrow(DistinctHosts(t))
  }

  distinct_shells$shell_label = ShellLabels(distinct_shells$shell_name,
                                            distinct_shells$shell_hash,
                                            num_hosts)
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

  # Add the number of lines, joining on path, and compute lines/ms
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
  # Hack: we know benchmarks/auto.sh runs this on one machine
  distinct_shells_2 = DistinctShells(cachegrind, num_hosts = nrow(distinct_hosts))
  cachegrind %>%
    left_join(lines, by = c('path')) %>%
    select(-c(elapsed_secs, user_secs, sys_secs, max_rss_KiB)) %>% 
    left_join(distinct_shells_2, by = c('shell_name', 'shell_hash')) %>%
    select(-c(shell_name, shell_hash)) %>%
    mutate(filename = basename(path), filename_HREF = sourceUrl(path)) %>%
    select(-c(path)) ->
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
      arrange(filename, elapsed_ms) ->
      times_flat

    joined_cachegrind %>%
      select(c(shell_label, irefs, num_lines, filename, filename_HREF)) %>%
      arrange(filename, irefs) ->
      cachegrind_flat

  } else {

    times_flat = NA
    cachegrind_flat = NA

    # Elapsed seconds for each shell by platform and file
    joined_times %>%
      select(-c(lines_per_ms, user_ms, sys_ms, max_rss_MB)) %>% 
      spread(key = shell_label, value = elapsed_ms) %>%
      arrange(host_label, num_lines) %>%
      mutate(osh_to_bash_ratio = `osh-native` / bash) %>% 
      select(c(host_label, bash, dash, mksh, zsh,
               `osh-ovm`, `osh-cpython`, `osh-native`,
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
               `osh-ovm`, `osh-cpython`, `osh-native`,
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
               `osh-ovm`, `osh-cpython`, `osh-native`,
               num_lines, filename, filename_HREF)) ->
      max_rss

    Log('\n')
    Log('MAX RSS')
    print(max_rss)

    Log('\n')
    Log('joined_cachegrind has %d rows', nrow(joined_cachegrind))
    print(joined_cachegrind)
    #print(joined_cachegrind %>% filter(path == 'benchmarks/testdata/configure-helper.sh'))

    # Cachegrind instructions by file
    joined_cachegrind %>%
      mutate(thousand_irefs_per_line = irefs / num_lines / 1000) %>%
      select(-c(irefs)) %>%
      spread(key = shell_label, value = thousand_irefs_per_line) %>%
      arrange(num_lines) %>%
      select(c(bash, dash, mksh, `osh-native`,
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

  precision = SamePrecision(0)  # lines per ms
  writeCsv(times_summary, file.path(out_dir, 'summary'), precision)

  precision = ColumnPrecision(list(), default = 1)
  writeTsv(cachegrind_summary, file.path(out_dir, 'cachegrind_summary'), precision)

  if (!is.na(times_flat)) {
    precision = SamePrecision(0)
    writeTsv(times_flat, file.path(out_dir, 'times_flat'), precision)
  }

  if (!is.na(cachegrind_flat)) {
    precision = SamePrecision(0)
    writeTsv(cachegrind_flat, file.path(out_dir, 'cachegrind_flat'), precision)
  }

  if (!is.na(elapsed)) {  # equivalent to no-host
    # Round to nearest millisecond, but the ratio has a decimal point.
    precision = ColumnPrecision(list(osh_to_bash_ratio = 1), default = 0)
    writeCsv(elapsed, file.path(out_dir, 'elapsed'), precision)

    precision = SamePrecision(0)
    writeCsv(rate, file.path(out_dir, 'rate'), precision)

    writeCsv(max_rss, file.path(out_dir, 'max_rss'))

    precision = SamePrecision(1)
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

  Log('distinct_hosts')
  print(distinct_hosts)
  Log('')

  Log('distinct_shells')
  print(distinct_shells)
  Log('')

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

WriteSimpleProvenance = function(provenance, out_dir) {
  Log('provenance')
  print(provenance)
  Log('')

  # Legacy: add $shell_name, because "$shell_basename-$shell_hash" is what
  # benchmarks/id.sh publish-shell-id uses
  provenance %>%
    mutate(shell_name = basename(sh_path)) %>%
    distinct(shell_label, shell_name, shell_hash) ->
    distinct_shells 

  Log('distinct_shells')
  print(distinct_shells)
  Log('')

  provenance %>% distinct(host_label, host_name, host_hash) -> distinct_hosts

  WriteProvenance(distinct_hosts, distinct_shells, out_dir, tsv = T)
}

RuntimeReport = function(in_dir, out_dir) {
  times = readTsv(file.path(in_dir, 'times.tsv'))
   
  gc_stats = readTsv(file.path(in_dir, 'gc_stats.tsv'))
  provenance = readTsv(file.path(in_dir, 'provenance.tsv'))

  times %>% filter(status != 0) -> failed
  if (nrow(failed) != 0) {
    print(failed)
    stop('Some osh-runtime tasks failed')
  }

  # Joins:
  # times <= sh_path => provenance
  # times <= join_id, host_name => gc_stats

  # TODO: provenance may have rows from 2 machines.  Could validate them and
  # deduplicate.

  # It should have (host_label, host_name, host_hash)
  #                (shell_label, sh_path, shell_hash)
  provenance %>%
    mutate(host_label = host_name, shell_label = ShellLabelFromPath(sh_path)) ->
    provenance

  provenance %>% distinct(sh_path, shell_label) -> label_lookup

  Log('label_lookup')
  print(label_lookup)

  # Join with provenance for host label and shell label
  times %>%
    select(-c(status)) %>%
    mutate(elapsed_ms = elapsed_secs * 1000,
           user_ms = user_secs * 1000,
           sys_ms = sys_secs * 1000,
           max_rss_MB = max_rss_KiB * 1024 / 1e6) %>%
    select(-c(elapsed_secs, user_secs, sys_secs, max_rss_KiB)) %>%
    left_join(label_lookup, by = c('sh_path')) %>%
    select(-c(sh_path)) ->
    details

  Log('details')
  print(details)

  # Sort by osh elapsed ms.
  details %>%
    select(-c(task_id, user_ms, sys_ms, max_rss_MB)) %>%
    spread(key = shell_label, value = elapsed_ms) %>%
    mutate(py_bash_ratio = `osh-cpython` / bash) %>%
    mutate(native_bash_ratio = `osh-native` / bash) %>%
    arrange(workload, host_name) %>%
    select(c(workload, host_name,
             bash, dash, `osh-cpython`, `osh-native`,
             py_bash_ratio, native_bash_ratio)) ->

    elapsed

  Log('elapsed')
  print(elapsed)

  details %>%
    select(-c(task_id, elapsed_ms, user_ms, sys_ms)) %>%
    spread(key = shell_label, value = max_rss_MB) %>%
    mutate(py_bash_ratio = `osh-cpython` / bash) %>%
    mutate(native_bash_ratio = `osh-native` / bash) %>%
    arrange(workload, host_name) %>%
    select(c(workload, host_name,
             bash, dash, `osh-cpython`, `osh-native`,
             py_bash_ratio, native_bash_ratio)) ->
    max_rss

  Log('max rss')
  print(max_rss)

  details %>% 
    select(c(task_id, host_name, workload, elapsed_ms, max_rss_MB)) %>%
    mutate(join_id = sprintf("gc-%d", task_id)) %>%
    select(-c(task_id)) ->
    gc_details

  Log('GC stats')
  print(gc_stats)

  gc_stats %>%
    left_join(gc_details, by = c('join_id', 'host_name')) %>%
    select(-c(join_id, roots_capacity, objs_capacity)) %>%
    # Do same transformations as GcReport()
    mutate(allocated_MB = bytes_allocated / 1e6) %>%
    select(-c(bytes_allocated)) %>%
    rename(num_gc_done = num_collections) %>%
    # Put these columns first
    relocate(workload, host_name,
             elapsed_ms, max_gc_millis, total_gc_millis,
             allocated_MB, max_rss_MB, num_allocated) ->
    gc_stats

  Log('After GC stats')
  print(gc_stats)

  WriteSimpleProvenance(provenance, out_dir)

  precision = ColumnPrecision(list(bash = 0, dash = 0, `osh-cpython` = 0,
                                   `osh-native` = 0))
  writeTsv(elapsed, file.path(out_dir, 'elapsed'), precision)
  writeTsv(max_rss, file.path(out_dir, 'max_rss'))  # default is OK

  precision2 = ColumnPrecision(list(max_rss_MB = 1, allocated_MB = 1),
                               default = 0)
  writeTsv(gc_stats, file.path(out_dir, 'gc_stats'), precision2)
  writeTsv(details, file.path(out_dir, 'details'), precision2)

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

  # paths look like _tmp/ovm-build/bin/clang/oils_cpp.stripped
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
  # - oils_cpp doesn't implement unicode LANG=C
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

  precision = ColumnPrecision(list(max_rss_MB = 1), default = 0)
  writeTsv(details, file.path(out_dir, 'details'), precision)

  writeTsv(hello, file.path(out_dir, 'hello'), precision)
  writeTsv(fib, file.path(out_dir, 'fib'), precision)
  writeTsv(word_freq, file.path(out_dir, 'word_freq'), precision)
  writeTsv(parse_help, file.path(out_dir, 'parse_help'), precision)

  writeTsv(bubble_sort, file.path(out_dir, 'bubble_sort'), precision)
  writeTsv(palindrome, file.path(out_dir, 'palindrome'), precision)

  WriteProvenance(distinct_hosts, distinct_shells, out_dir, tsv = T)
}

WriteOneTask = function(times, out_dir, task_name, precision) {
  times %>%
    filter(task == task_name) %>%
    select(-c(task)) -> subset

  writeTsv(subset, file.path(out_dir, task_name), precision)
}

GcReport = function(in_dir, out_dir) {
  times = read.table(file.path(in_dir, 'raw/times.tsv'), header=T)
  gc_stats = read.table(file.path(in_dir, 'stage1/gc_stats.tsv'), header=T)

  times %>% filter(status != 0) -> failed
  if (nrow(failed) != 0) {
    print(failed)
    stop('Some gc tasks failed')
  }

  # Change units and order columns
  times %>%
    arrange(task) %>%
    mutate(elapsed_ms = elapsed_secs * 1000,
           user_ms = user_secs * 1000,
           sys_ms = sys_secs * 1000,
           max_rss_MB = max_rss_KiB * 1024 / 1e6,
           shell_label = ShellLabelFromPath(sh_path)
           ) %>%
    select(c(join_id, task, elapsed_ms, user_ms, sys_ms, max_rss_MB, shell_label,
             shell_runtime_opts)) ->
    times

  # Join and order columns
  gc_stats %>% left_join(times, by = c('join_id')) %>% 
    arrange(desc(task)) %>%
    mutate(allocated_MB = bytes_allocated / 1e6) %>%
    # try to make the table skinnier
    rename(num_gc_done = num_collections) %>%
    select(task, elapsed_ms, max_gc_millis, total_gc_millis,
           allocated_MB, max_rss_MB, num_allocated,
           num_gc_points, num_gc_done, gc_threshold, num_growths, max_survived,
           shell_label) ->
    gc_stats

  times %>% select(-c(join_id)) -> times


  precision = ColumnPrecision(list(max_rss_MB = 1, allocated_MB = 1),
                              default = 0)

  writeTsv(times, file.path(out_dir, 'times'), precision)
  writeTsv(gc_stats, file.path(out_dir, 'gc_stats'), precision)

  tasks = c('parse.configure-coreutils',
            'parse.configure-cpython',
            'parse.abuild',
            'ex.compute-fib',
            'ex.bashcomp-parse-help',
            'ex.abuild-print-help')
  # Write out separate rows
  for (task in tasks) {
    WriteOneTask(times, out_dir, task, precision)
  }
}

GcCachegrindReport = function(in_dir, out_dir) {
  times = readTsv(file.path(in_dir, 'raw/times.tsv'))
  counts = readTsv(file.path(in_dir, 'stage1/cachegrind.tsv'))

  times %>% filter(status != 0) -> failed
  if (nrow(failed) != 0) {
    print(failed)
    stop('Some gc tasks failed')
  }

  print(times)
  print(counts)

  counts %>% left_join(times, by = c('join_id')) %>% 
    mutate(million_irefs = irefs / 1e6) %>%
    select(c(million_irefs, task, sh_path, shell_runtime_opts)) %>%
    arrange(shell_runtime_opts, million_irefs) ->
    counts

  precision = NULL
  tasks = c('parse.abuild', 'ex.compute-fib')
  for (task in tasks) {
    WriteOneTask(counts, out_dir, task, precision)
  }
}

MyCppReport = function(in_dir, out_dir) {
  times = readTsv(file.path(in_dir, 'benchmark-table.tsv'))
  print(times)

  times %>% filter(status != 0) -> failed
  if (nrow(failed) != 0) {
    print(failed)
    stop('Some mycpp tasks failed')
  }

  # Don't care about elapsed and system
  times %>% select(-c(status, elapsed_secs, bin, task_out)) %>%
    mutate(example_name_HREF = mycppUrl(example_name),
           user_ms = user_secs * 1000, 
           sys_ms = sys_secs * 1000, 
           max_rss_MB = max_rss_KiB * 1024 / 1e6) %>%
    select(-c(user_secs, sys_secs, max_rss_KiB)) ->
    details

  details %>% select(-c(sys_ms, max_rss_MB)) %>%
    spread(key = impl, value = user_ms) %>%
    mutate(`C++ : Python` = `C++` / Python) %>%
    arrange(`C++ : Python`) ->
    user_time

  details %>% select(-c(user_ms, max_rss_MB)) %>%
    spread(key = impl, value = sys_ms) %>%
    mutate(`C++ : Python` = `C++` / Python) %>%
    arrange(`C++ : Python`) ->
    sys_time

  details %>% select(-c(user_ms, sys_ms)) %>%
    spread(key = impl, value = max_rss_MB) %>%
    mutate(`C++ : Python` = `C++` / Python) %>%
    arrange(`C++ : Python`) ->
    max_rss

  # Sometimes it speeds up by more than 10x
  precision1 = ColumnPrecision(list(`C++ : Python` = 3), default = 0)
  writeTsv(user_time, file.path(out_dir, 'user_time'), precision1)
  writeTsv(sys_time, file.path(out_dir, 'sys_time'), precision1)

  precision2 = ColumnPrecision(list(`C++ : Python` = 2), default = 1)
  writeTsv(max_rss, file.path(out_dir, 'max_rss'), precision2)

  writeTsv(details, file.path(out_dir, 'details'))
}

UftraceTaskReport = function(env, task_name, summaries) {
  # Need this again after redirect
  MaybeDisableColor(stdout())

  task_env = env[[task_name]]

  untyped = task_env$untyped
  typed = task_env$typed
  strings = task_env$strings
  slabs = task_env$slabs
  reserve = task_env$reserve

  string_overhead = 13
  strings %>% mutate(obj_len = str_len + string_overhead) -> strings

  # TODO: Output these totals PER WORKLOAD, e.g. parsing big/small, executing
  # big/small
  #
  # And then zoom in on distributions as well

  num_allocs = nrow(untyped)
  total_bytes = sum(untyped$obj_len)

  untyped %>% group_by(obj_len) %>% count() %>% ungroup() -> untyped_hist
  
  untyped_hist %>%
    mutate(n_less_than = cumsum(n),
           percent = n_less_than * 100.0 / num_allocs) ->
    alloc_sizes

  allocs_16_bytes_or_less = alloc_sizes %>% filter(obj_len == 16) %>% select(percent)
  allocs_32_bytes_or_less = alloc_sizes %>% filter(obj_len == 32) %>% select(percent)
  allocs_64_bytes_or_less = alloc_sizes %>% filter(obj_len == 64) %>% select(percent)
  Log('Percentage of allocs less than 32 bytes: %.1f', allocs_32_bytes_or_less)

  options(tibble.print_min=25)

  Log('')
  Log('All allocations')
  print(alloc_sizes %>% head(22))
  print(alloc_sizes %>% tail(5))

  Log('')
  Log('Common Sizes')
  print(untyped_hist %>% arrange(desc(n)) %>% head(8))

  Log('')
  Log('    %s total allocations, total bytes = %s', commas(num_allocs), commas(total_bytes))
  Log('')

  Log('Typed allocations')

  num_typed = nrow(typed)

  typed %>% group_by(func_name) %>% count() %>% ungroup() %>%
    mutate(percent = n * 100.0 / num_typed) %>%
    arrange(desc(n)) -> most_common_types

  print(most_common_types %>% head(20))
  print(most_common_types %>% tail(5))

  lists = typed %>% filter(str_starts(func_name, ('List<')))
  #print(lists)

  num_lists = nrow(lists)
  total_list_bytes = num_lists * 24  # sizeof List<T> head is hard-coded

  Log('')
  Log('%s typed allocs, including %s List<T>', commas(num_typed), commas(num_lists))
  Log('%.2f%% of allocs are typed', num_typed * 100 / num_allocs)
  Log('')

  #
  # Strings
  #

  num_strings = nrow(strings)
  total_string_bytes = sum(strings$obj_len)

  strings %>% group_by(str_len) %>% count() %>% ungroup() %>%
    mutate(n_less_than = cumsum(n),
           percent = n_less_than * 100.0 / num_strings) ->
    string_lengths

  strs_7_bytes_or_less = string_lengths %>% filter(str_len == 7) %>% select(percent)
  strs_15_bytes_or_less = string_lengths %>% filter(str_len == 15) %>% select(percent)

  # Parse workload
  # 62% of strings <= 6 bytes
  # 84% of strings <= 14 bytes

  Log('Str - NewStr() and OverAllocatedStr()')
  print(string_lengths %>% head(16))
  print(string_lengths %>% tail(5))
  Log('')

  Log('%s string allocations, total length = %s, total bytes = %s', commas(num_strings),
      commas(sum(strings$str_len)), commas(total_string_bytes))
  Log('')
  Log('%.2f%% of allocs are strings', num_strings * 100 / num_allocs)
  Log('%.2f%% of bytes are strings', total_string_bytes * 100 / total_bytes)
  Log('')

  #
  # Slabs
  #

  Log('NewSlab()')

  num_slabs = nrow(slabs)
  slabs %>% group_by(slab_len) %>% count() %>% ungroup() %>%
    mutate(n_less_than = cumsum(n),
           percent = n_less_than * 100.0 / num_slabs) ->
    slab_lengths

  slabs %>% group_by(func_name) %>% count() %>% ungroup() %>%
    arrange(desc(n)) -> slab_types

  Log('  Lengths')
  print(slab_lengths %>% head())
  print(slab_lengths %>% tail(5))
  Log('')

  Log('  Slab Types')
  print(slab_types %>% head())
  print(slab_types %>% tail(5))
  Log('')

  total_slab_items = sum(slabs$slab_len)

  Log('%s slabs, total items = %s', commas(num_slabs),
      commas(sum(slabs$slab_len)))
  Log('%.2f%% of allocs are slabs', num_slabs * 100 / num_allocs)
  Log('')

  #
  # reserve() calls
  #

  # There should be strictly more List::reserve() calls than NewSlab

  Log('::reserve(int n)')
  Log('')

  num_reserve = nrow(reserve)
  reserve %>% group_by(num_items) %>% count() %>% ungroup() %>%
    mutate(n_less_than = cumsum(n),
           percent = n_less_than * 100.0 / num_reserve) ->
    reserve_args

  Log('  Num Items')
  print(reserve_args %>% head(15))
  print(reserve_args %>% tail(5))
  Log('')

  Log('%s reserve() calls, total items = %s', commas(num_reserve),
      commas(sum(reserve$num_items)))
  Log('')

  # Accounting for all allocations!
  Log('Untyped: %s', commas(num_allocs))
  Log('Typed + Str + Slab: %s', commas(num_typed + num_strings + num_slabs))
  Log('')

  num_other_typed = num_typed - num_lists

  # Summary table
  stats = tibble(task = task_name,
                 total_bytes_ = commas(total_bytes),
                 num_allocs_ = commas(num_allocs),
                 sum_typed_strs_slabs = commas(num_typed + num_strings + num_slabs),
                 num_reserve_calls = commas(num_reserve),

                 percent_list_allocs = Percent(num_lists, num_allocs),
                 percent_slab_allocs = Percent(num_slabs, num_allocs),
                 percent_string_allocs = Percent(num_strings, num_allocs),
                 percent_other_typed_allocs = Percent(num_other_typed, num_allocs),

                 percent_list_bytes = Percent(total_list_bytes, total_bytes),
                 percent_string_bytes = Percent(total_string_bytes, total_bytes),

                 allocs_16_bytes_or_less = sprintf('%.1f%%', allocs_16_bytes_or_less),
                 allocs_32_bytes_or_less = sprintf('%.1f%%', allocs_32_bytes_or_less),
                 allocs_64_bytes_or_less = sprintf('%.1f%%', allocs_64_bytes_or_less),

                 strs_7_bytes_or_less = sprintf('%.1f%%', strs_7_bytes_or_less),
                 strs_15_bytes_or_less = sprintf('%.1f%%', strs_15_bytes_or_less),
                 )
  summaries$stats[[task_name]] = stats

  summaries$most_common_types[[task_name]] = most_common_types
}

LoadUftraceTsv = function(in_dir, env) {
  for (task in list.files(in_dir)) {
    Log('Loading data for task %s', task)
    base_dir = file.path(in_dir, task)

    task_env = new.env()
    env[[task]] = task_env

    # TSV file, not CSV
    task_env$untyped = readTsv(file.path(base_dir, 'all-untyped.tsv'))
    task_env$typed = readTsv(file.path(base_dir, 'typed.tsv'))
    task_env$strings = readTsv(file.path(base_dir, 'strings.tsv'))
    task_env$slabs = readTsv(file.path(base_dir, 'slabs.tsv'))
    task_env$reserve = readTsv(file.path(base_dir, 'reserve.tsv'))

    # median string length is 4, mean is 9.5!
    Log('UNTYPED')
    print(summary(task_env$untyped))
    Log('')

    Log('TYPED')
    print(summary(task_env$typed))
    Log('')

    Log('STRINGS')
    print(summary(task_env$strings))
    Log('')

    Log('SLABS')
    print(summary(task_env$slabs))
    Log('')

    Log('RESERVE')
    print(summary(task_env$reserve))
    Log('')
  }
}

Percent = function(n, total) {
  sprintf('%.1f%%', n * 100.0 / total)
}

PrettyPrintLong = function(d) {
  tr = t(d)  # tranpose

  row_names = rownames(tr)

  for (i in 1:nrow(tr)) {
    row_name = row_names[i]
    cat(sprintf('%26s', row_name))  # calculated min width manually
    cat(sprintf('%20s', tr[i,]))
    cat('\n')

    # Extra spacing
    if (row_name %in% c('num_reserve_calls',
                        'percent_string_bytes',
                        'percent_other_typed_allocs',
                        'allocs_64_bytes_or_less')) {
      cat('\n')
    }
  }
}


UftraceReport = function(env, out_dir) {
  # summaries$stats should be a list of 1-row data frames
  # summaries$top_types should be a list of types
  summaries = new.env()

  for (task_name in names(env)) {
    report_out = file.path(out_dir, paste0(task_name, '.txt'))

    Log('Making report for task %s -> %s', task_name, report_out)

    sink(file = report_out)
    UftraceTaskReport(env, task_name, summaries)
    sink()  # reset
  }
  Log('')

  # Concate all the data frames added to summary
  stats = bind_rows(as.list(summaries$stats))

  sink(file = file.path(out_dir, 'summary.txt'))
  #print(stats)
  #Log('')

  PrettyPrintLong(stats)
  Log('')

  mct = summaries$most_common_types
  for (task_name in names(mct)) {
    Log('Common types in workload %s', task_name)
    Log('')

    print(mct[[task_name]] %>% head(5))
    Log('')
  }
  sink()

  # For the REPL
  return(list(stats = stats))
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

  } else if (action == 'gc-cachegrind') {
    GcCachegrindReport(in_dir, out_dir)

  } else if (action == 'mycpp') {
    MyCppReport(in_dir, out_dir)

  } else if (action == 'uftrace') {
    d = new.env()
    LoadUftraceTsv(in_dir, d)
    UftraceReport(d, out_dir)

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
