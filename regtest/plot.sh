#!/usr/bin/env bash
#
# Plot stats for regtest/aports
#
# This file was generated with Claude Code.
#
# I wanted to try out gnuplot.  TODO: I think moving back to R is better!  I
# can't read gnuplot!
#
# Usage:
#   regtest/plot.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

deps() {
  sudo apt-get install gnuplot
}

make-cpu-tsv() {
  local input_file=${1:-_tmp/aports-report/2025-11-13-main-full/proc-log/stat.txt}

  # Extract only lines that start with timestamp followed by "cpu " (not cpu0, cpu1, etc.)
  # Field 5 is the idle time (0-indexed: timestamp=0, cpu=1, user=2, nice=3, system=4, idle=5)
  awk '/^[0-9]+ cpu / { print $1 "\t" $5 }' "$input_file"
}

plot() {
  local format=${1:-png}
  local tsv_file=${2:-_tmp/cpu_idle.tsv}
  local output_file=${3:-cpu_idle.$format}

  echo "Generating $tsv_file..."
  make-cpu-tsv > "$tsv_file"

  # Create gnuplot script
  local terminal_cmd
  case "$format" in
    png)
      terminal_cmd="set terminal pngcairo size 1200,800 enhanced font 'Arial,12'"
      ;;
    svg)
      terminal_cmd="set terminal svg size 1200,800 enhanced font 'Arial,12'"
      ;;
    *)
      echo "Error: Unsupported format '$format'. Use 'png' or 'svg'."
      return 1
      ;;
  esac

  gnuplot <<EOF
$terminal_cmd
set output '$output_file'

set title "CPU Idle Time Over Time"
set xlabel "Timestamp (Unix time)"
set ylabel "CPU Idle Time (jiffies)"
set grid

plot '$tsv_file' using 1:2 with lines title 'CPU Idle'
EOF

  echo "Created $output_file"
}

task-five "$@"
