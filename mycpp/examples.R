#!/usr/bin/Rscript
#
# examples-- Analyze output of mycpp examples.
#
# Usage:
#   examples.R ACTION IN_DIR OUT_DIR

library(dplyr)
library(tidyr)  # spread()
library(stringr)

source('../benchmarks/common.R')  # assuming current dir is mycpp/

options(stringsAsFactors = F,
        # Make the report wide.  tibble.width doesn't appear to do this?
        width=200,
        tibble.print_max=Inf
)

Report = function(ctx) {
  ctx$examples %>% print()
  Log('')
  ctx$examples %>%
    spread(key = language, value = seconds) %>%
    mutate(speedup = `C++` / `Python`,
           percent = sprintf("%.1f", speedup * 100)
          ) %>%
    arrange(speedup) %>%
    print()
}

Load = function(in_dir) {
  list(
    examples = read.table(file.path(in_dir, 'mycpp-examples.tsv'), header=T)
  )
}

main = function(argv) {
  action = argv[[1]]

  if (action == 'report') {
    in_dir = argv[[2]]
    ctx = Load(in_dir)
    Report(ctx)

  } else if (action == 'compare') {
    Log('unimplemented')

  } else {
    Log("Invalid action '%s'", action)
    quit(status = 1)
  }
}

if (length(sys.frames()) == 0) {
  # increase ggplot font size globally
  #theme_set(theme_grey(base_size = 20))
  main(commandArgs(TRUE))
}
