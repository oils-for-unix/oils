#!/usr/bin/Rscript
#
# common.R - Shared R functions.

Log = function(fmt, ...) {
  cat(sprintf(fmt, ...))
  cat('\n')
}

Banner = function(fmt, ...) {
  cat('===== '); Log(fmt, ...)
  cat('\n')
}

ShowFrame = function(description, df) {
  Log(description)
  print(df)
  Log('')
}

ShowValue = function(msg, ...) {
  cat('-- '); Log(msg, ...)
  Log('')
}

# Same precision for all columns.
SamePrecision = function(precision = 1) {
  return(function(column_name) {
    precision
  })
}

# Precision by column.
ColumnPrecision = function(precision_map, default = 1) {
  return(function(column_name) {
    p = precision_map[[column_name]]
    if (is.null(p)) {
      default
    } else {
      p
    }
  })
}

# Write a CSV file along with a schema.
#
# precision: list(column name -> integer precision)
writeCsv = function(table, prefix, precision_func = NULL, tsv = F) {
  if (tsv) {
    data_out_path = paste0(prefix, '.tsv')
    write.table(table, data_out_path, row.names = F, sep = '\t', quote = F)
  } else {
    data_out_path = paste0(prefix, '.csv')
    write.csv(table, data_out_path, row.names = F)
  }

  getFieldType = function(field_name) { typeof(table[[field_name]]) }

  if (is.null(precision_func)) {
    precision_func = function(column_name) { 1 }
  }

  types_list = lapply(names(table), getFieldType)
  precision_list = lapply(names(table), precision_func)
  print(precision_list)

  schema = data_frame(
    column_name = names(table),
    type = as.character(types_list),
    precision = as.character(precision_list)
  )
  if (tsv) {
    schema_out_path = paste0(prefix, '.schema.tsv')
    write.table(schema, schema_out_path, row.names = F, sep = '\t', quote = F)
  } else {
    schema_out_path = paste0(prefix, '.schema.csv')
    write.csv(schema, schema_out_path, row.names = F)
  }
}

readTsv = function(path) {
  # quote = '' means disable quoting
  read.table(path, header = T, sep = '\t', quote = '')
}

writeTsv = function(table, prefix, precision_func = NULL) {
  writeCsv(table, prefix, precision_func = precision_func, tsv = T)
}

