#!/usr/bin/env bash
#
# Plot stats for regtest/aports
#
# This file was started with Claude Code.
#
# I wanted to try out gnuplot.  TODO: I think moving back to R is better -- I
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

readonly STAT_FILE=_tmp/aports-report/2025-11-13-main-full/proc-log/stat.txt

make-cpu-tsv() {
  local input_file=${1:-$STAT_FILE}

  # Extract only lines that start with timestamp followed by "cpu " (not cpu0, cpu1, etc.)
  # Field 5 is the idle time (0-indexed: timestamp=0, cpu=1, user=2, nice=3, system=4, idle=5)
  awk '/^[0-9]+ cpu / { print $1 "\t" $6 }' "$input_file"
}

totals() {
  local input_file=${1:-$STAT_FILE}

  awk '
  /^[0-9]+ cpu[ ]/ {
    user += $3
    sys += $5
    idle += $6 
  }
  END {
    print user
    print sys
    print idle

    print user/sys
    # Hm, there is a lot of idle time
    print user/idle
  }
  ' "$input_file"

  echo
  wc -l $input_file
}

col-diff() {
  local input_file=${1:-$STAT_FILE}

  awk '
  /^[0-9]+ cpu[ ]/ {
    if (NR == 1) {
      prev_time = $1
      prev_user = $3
      prev_sys = $5
      prev_idle = $6
    } else {
      time = $1
      user = $3
      sys = $5
      idle = $6

      #print time - prev_time
      #print user - prev_user
      #print sys - prev_sys
      print idle - prev_idle

      prev_time = time
      prev_user = user
      prev_sys = sys
      prev_idle = idle
    }
  }
  ' "$input_file"
}

col-diff-hist() {
  col-diff | sort | uniq -c | sort -n
}

col-diff-plot() {
  # Silly but convenient method of plotting!

  col-diff | awk '
  # Store values and find max
  {
    values[NR] = $1
    if ($1 > max) max = $1
  }

  END {
    # Scale and print
    for (i = 1; i <= NR; i++) {
      bar_length = int(values[i] / max * 50)  # Scale to 50 chars
      printf "%6d| ", values[i]
      for (j = 0; j < bar_length; j++) {
        printf "_"
      }
      printf "\n"
    }
  }
  '
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
