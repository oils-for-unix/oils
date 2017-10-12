#!/usr/bin/python
# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Reads a CSV file on stdin, and prints an an HTML table on stdout.

The static HTML can then be made made dynamic with JavaScript, e.g. jQuery
DataTable.

NOTE: This detects if the column is numeric and outputs <colgroup> entries to
indicate it.
"""

import cgi
import csv
import optparse
import sys


def CreateOptionsParser():
  p = optparse.OptionParser()

  # We are taking a path, and not using stdin, because we read it twice.
  p.add_option(
      '--col-format', dest='col_formats', metavar="'COLNAME FMT'", type='str',
      default=[], action='append',
      help='Add HTML links to the named column, using the given Python '
           '.format() string')

  p.add_option(
      '--def', dest='defs', metavar="'NAME VALUE'", type='str',
      default=[], action='append',
      help='Define varaibles for use in format strings')

  p.add_option(
      '--as-percent', dest='percent_cols', metavar="COLNAME", type='str',
      default=[], action='append',
      help='Format this floating point column as a percentage string')

  # TODO: We could include this by default, and then change all the HTML to
  # have <div> placeholders instead of <table>.
  p.add_option(
      '--table', dest='table', default=False, action='store_true',
      help='Add <table></table> tags (useful for testing)')

  return p


def ParseSpec(arg_list):
  """Given an argument list, return a string -> string dictionary."""
  # The format string is passed the cell value.  Escaped as HTML?
  d = {}
  for s in arg_list:
    try:
      name, value = s.split(' ', 1)
    except ValueError:
      raise RuntimeError('Invalid column format %r' % s)
    d[name] = value
  return d


def PrintRow(row, col_names, col_formats, defs, percent_cols):
  """Print a CSV row as HTML, using the given formatting.

  Returns:
    An array of booleans indicating whether each cell is a number.
  """
  is_number_flags = [False] * len(col_names)

  for i, cell in enumerate(row):
    # The cell as a string.  By default we leave it as is; it may be mutated
    # below.
    cell_str = cell
    css_class = ''  # CSS class for the cell.
    col_name = col_names[i]  # column that the cell is under

    # Does the cell look like a float?
    try:
      cell_float = float(cell)
      if col_name in percent_cols:  # Floats can be formatted as percentages.
        cell_str = '{:.1f}%'.format(cell_float * 100)
      else:
        # Arbitrarily use 3 digits of precision for display
        cell_str = '{:.3f}'.format(cell_float)
      css_class = 'num'
      is_number_flags[i] = True
    except ValueError:
      pass

    # Does it look lik an int?
    try:
      cell_int = int(cell)
      cell_str = '{:,}'.format(cell_int)
      css_class = 'num'
      is_number_flags[i] = True
    except ValueError:
      pass

    # Special CSS class for R NA values.
    if cell_str.strip() == 'NA':
      css_class = 'num na'  # num should right justify; na should make it red
      is_number_flags[i] = True

    if css_class:
      print '    <td class="{}">'.format(css_class),
    else:
      print '    <td>',

    cell_safe = cgi.escape(cell_str)

    # If the cell has a format string, print it this way.

    fmt = col_formats.get(col_name)  # e.g. "../{date}.html"
    if fmt:
      # Copy variable bindings
      bindings = dict(defs)

      # Also let the format string use other column names.  TODO: Is there a
      # more efficient way?
      bindings.update(zip(col_names, [cgi.escape(c) for c in row]))

      bindings[col_name] = cell_safe

      print fmt.format(**bindings),  # no newline
    else:
      print cell_safe,  # no newline

    print '</td>'

  return is_number_flags


def ReadCsv(f):
  """Read the CSV file, returning the column names and rows."""
  c = csv.reader(f)

  # The first row of the CSV is assumed to be a header.  The rest are data.
  col_names = []
  rows = []
  for i, row in enumerate(c):
    if i == 0:
      col_names = row
      continue
    rows.append(row)
  return col_names, rows


def PrintColGroup(col_names, col_is_numeric):
  """Print HTML colgroup element, used for JavaScript sorting."""
  print '<colgroup>'
  for i, col in enumerate(col_names):
    # CSS class is used for sorting
    if col_is_numeric[i]:
      css_class = 'number'
    else:
      css_class = 'case-insensitive'

    # NOTE: id is a comment only; not used
    print '  <col id="{}" type="{}" />'.format(col, css_class)
  print '</colgroup>'


def main(argv):
  (opts, argv) = CreateOptionsParser().parse_args(argv)

  col_formats = ParseSpec(opts.col_formats)
  defs = ParseSpec(opts.defs)

  col_names, rows = ReadCsv(sys.stdin)

  for col in opts.percent_cols:
    if col not in col_names:
      raise RuntimeError('--percent-col %s is not a valid column' % col)

  # By default, we don't print the <table> bit -- that's up to the host page
  if opts.table:
    print '<table>'

  print '<thead>'
  for col in col_names:
    # change _ to space so long column names can wrap
    print '  <td>%s</td>' % cgi.escape(col.replace('_', ' '))
  print '</thead>'

  # Assume all columns are numeric at first.  Look at each row for non-numeric
  # values.
  col_is_numeric = [True] * len(col_names)

  print '<tbody>'
  for row in rows:
    print '  <tr>'
    is_number_flags = PrintRow(row, col_names, col_formats, defs,
                               opts.percent_cols)

    # If one cell in a column is not a number, then the whole cell isn't.
    for (i, is_number) in enumerate(is_number_flags):
      if not is_number:
        col_is_numeric[i] = False

    print '  </tr>'
  print '</tbody>'

  PrintColGroup(col_names, col_is_numeric)

  if opts.table:
    print '</table>'


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError, e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
