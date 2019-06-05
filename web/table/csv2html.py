#!/usr/bin/env python2
from __future__ import print_function
"""
csv2html.py

Usage:
  csv2html.py foo.csv

Attempts to read foo_schema.csv.  If not it assumes everything is a string.

Things it handles:

- table-sort.js integration <colgroup>
  - <table id="foo"> for making columns sortable
  - for choosing the comparator to use!
  - for highlighting on sort
- static / visual
  - Aligning right for number, left for strings.
  - highlighting NA numbers in red (only if it's considered a number)
  - formatting numbers to a certain precision
    - or displaying them as percentages
  - changing CSV headers like 'elapsed_ms' to 'elapsed ms'
  - Accepting a column with a '_HREF' suffix to make an HTML link
    - We could have something like type:
      string/anchor:shell-id
      string/href:shell-id
    - But the simple _HREF suffix is simpler.  Easier to write R code for.

Implementation notes:
- To align right: need a class on every cell, e.g. "num".  Can't do it through
  <colgroup>.
- To color, can use <colgroup>.  table-sort.js needs this.

TODO:
  Does it make sense to implement <rowspan> and <colspan> ?  It's nice for
  visualization.
"""

import cgi
import csv
import optparse
import os
import re
import sys


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


class NullSchema:
  def VerifyColumnNames(self, col_names):
    pass

  def IsNumeric(self, col_name):
    return False

  def ColumnIndexIsNumeric(self, index):
    return False

  def ColumnIndexIsInteger(self, index):
    return False

  def ColumnIndexHasHref(self, index):
    return False


INTEGER_TYPES = ('integer',)

# for sorting, right-justification
NUMERIC_TYPES = ('double', 'number') + INTEGER_TYPES


class Schema:
  def __init__(self, rows):
    schema_col_names = rows[0]
    assert 'column_name' in schema_col_names, schema_col_names
    assert 'type' in schema_col_names, schema_col_names

    # Schema columns
    s_cols = {}
    s_cols['column_name'] = []
    s_cols['type'] = []
    s_cols['precision'] = []
    for row in rows[1:]:
      for i, cell in enumerate(row):
        name = schema_col_names[i]
        s_cols[name].append(cell)

    self.type_lookup = dict(
        (name, t) for (name, t) in
        zip(s_cols['column_name'], s_cols['type']))

    # NOTE: it's OK if precision is missing.
    self.precision_lookup = dict(
        (name, p) for (name, p) in
        zip(s_cols['column_name'], s_cols['precision']))

    #log('SCHEMA %s', schema_col_names)
    #log('type_lookup %s', self.type_lookup)
    #log('precision_lookup %s', self.precision_lookup)

    self.col_names = None
    self.col_has_href = None

  def VerifyColumnNames(self, col_names):
    """Assert that the column names we got are all in the schema."""
    for name in col_names:
      log('%s : %s', name, self.type_lookup[name])

    n = len(col_names)
    self.col_has_href = [False] * n
    for i in xrange(n-1):
      this_name, next_name= col_names[i], col_names[i+1]
      if this_name + '_HREF' == next_name:
        self.col_has_href[i] = True

    log('href: %s', self.col_has_href)
    self.col_names = col_names

  def IsNumeric(self, col_name):
    return self.type_lookup[col_name] in NUMERIC_TYPES

  def ColumnIndexIsNumeric(self, index):
    col_name = self.col_names[index]
    return self.IsNumeric(col_name)

  def ColumnIndexIsInteger(self, index):
    col_name = self.col_names[index]
    return self.type_lookup[col_name] in INTEGER_TYPES

  def ColumnIndexHasHref(self, index):
    """
    Is the next one?
    """
    return self.col_has_href[index]

  def ColumnPrecision(self, index):
    col_name = self.col_names[index]
    return self.precision_lookup.get(col_name, 1)  # default is arbitrary


def PrintRow(row, schema):
  """Print a CSV row as HTML, using the given formatting.

  Returns:
    An array of booleans indicating whether each cell is a number.
  """
  i = 0
  n = len(row)
  while True:
    if i == n:
      break

    cell = row[i]
    css_classes = []
    cell_str = cell  # by default, we don't touch it

    if schema.ColumnIndexIsInteger(i):
      css_classes.append('num')  # right justify

      try:
        cell_int = int(cell)
      except ValueError:
        pass  # NA?
      else:
        # commas AND floating point
        cell_str = '{:,}'.format(cell_int)

    # Look up by index now?
    elif schema.ColumnIndexIsNumeric(i):
      css_classes.append('num')  # right justify

      try:
        cell_float = float(cell)
      except ValueError:
        pass  # NA
      else:
        # commas AND floating point to a given precision
        precision = schema.ColumnPrecision(i)
        cell_str = '{0:,.{precision}f}'.format(cell_float, precision=precision)

      # Percentage
      #cell_str = '{:.1f}%'.format(cell_float * 100)

    # Special CSS class for R NA values.
    if cell.strip() == 'NA':
      css_classes.append('na')  # make it red

    if css_classes:
      print('      <td class="{}">'.format(' '.join(css_classes)), end=' ')
    else:
      print('      <td>', end=' ')

    # Advance to next row if it's an _HREF.
    if schema.ColumnIndexHasHref(i):
      i += 1
      href = row[i]
      s = '<a href="%s">%s</a>' % (cgi.escape(href), cgi.escape(cell_str))
    else:
      s = cgi.escape(cell_str)

    print(s, end=' ')
    print('</td>')

    i += 1


def PrintColGroup(col_names, schema):
  """Print HTML colgroup element, used for JavaScript sorting."""
  print('  <colgroup>')
  for i, col in enumerate(col_names):
    if col.endswith('_HREF'):
      continue

    # CSS class is used for sorting
    if schema.IsNumeric(col):
      css_class = 'number'
    else:
      css_class = 'case-insensitive'

    # NOTE: id is a comment only; not used
    print('    <col id="{}" type="{}" />'.format(col, css_class))
  print('  </colgroup>')


def PrintTable(css_id, schema, col_names, rows, css_class_pattern):
  if css_class_pattern:
    css_class, r = css_class_pattern.split(None, 2)
    cell_regex = re.compile(r)
  else:
    css_class = None
    cell_regex = None

  print('<table id="%s">' % css_id)
  print('  <thead>')
  print('    <tr>')
  for i, col in enumerate(col_names):
    if col.endswith('_HREF'):
      continue
    heading_str = cgi.escape(col.replace('_', ' '))
    if schema.ColumnIndexIsNumeric(i):
      print('    <td class="num">%s</td>' % heading_str)
    else:
      print('    <td>%s</td>' % heading_str)
  print('    </tr>')
  print('  </thead>')

  print('  <tbody>')
  for row in rows:

    # TODO: There should be a special column called CSS_CLASS.  Output that
    # from R.
    row_class = ''
    if cell_regex:
      for cell in row:
        if cell_regex.search(cell):
          row_class = 'class="%s"' % css_class
          break

    print('    <tr {}>'.format(row_class))

    PrintRow(row, schema)
    print('    </tr>')
  print('  </tbody>')

  PrintColGroup(col_names, schema)

  print('</table>')


def ReadFile(f, tsv=False):
  """Read the CSV file, returning the column names and rows."""

  if tsv:
    c = csv.reader(f, delimiter='\t', doublequote=False,
                   quoting=csv.QUOTE_NONE)
  else:
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


def CreateOptionsParser():
  p = optparse.OptionParser()

  # We are taking a path, and not using stdin, because we read it twice.
  p.add_option(
      '--schema', dest='schema', metavar="PATH", type='str',
      help='Path to the schema.')
  p.add_option(
      '--tsv', dest='tsv', default=False, action='store_true',
      help='Read input in TSV format')
  p.add_option(
      '--css-class-pattern', dest='css_class_pattern', type='str',
      help='A string of the form CSS_CLASS:PATTERN.  If the cell contents '
           'matches the pattern, then apply the given CSS class. '
           'Example: osh:^osh')
  return p


def main(argv):
  (opts, argv) = CreateOptionsParser().parse_args(argv[1:])

  try:
    csv_path = argv[0]
  except IndexError:
    raise RuntimeError('Expected CSV filename.')

  schema = None
  if opts.schema:
    try:
      schema_f = open(opts.schema)
    except IOError as e:
      raise RuntimeError('Error opening schema: %s' %  e)
  else:
    if csv_path.endswith('.csv'):
      schema_path = csv_path.replace('.csv', '.schema.csv')
    elif csv_path.endswith('.tsv'):
      schema_path = csv_path.replace('.tsv', '.schema.tsv')
    else:
      raise AssertionError(csv_path)

    log('schema path %s', schema_path)
    try:
      schema_f = open(schema_path)
    except IOError:
      schema_f = None  # allowed to have no schema

  if schema_f:
    if opts.tsv:
      r = csv.reader(schema_f, delimiter='\t', doublequote=False,
                     quoting=csv.QUOTE_NONE)
    else:
      r = csv.reader(schema_f)

    schema = Schema(list(r))
  else:
    schema = NullSchema()
    # Default string schema

  log('schema %s', schema)

  with open(csv_path) as f:
    col_names, rows = ReadFile(f, opts.tsv)

  schema.VerifyColumnNames(col_names)

  filename = os.path.basename(csv_path)
  css_id, _ = os.path.splitext(filename)
  PrintTable(css_id, schema, col_names, rows, opts.css_class_pattern)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
