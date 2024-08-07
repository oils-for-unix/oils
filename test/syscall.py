#!/usr/bin/env python2
"""test/syscall.py

Print a results table.

Input looks like

01-dash
01-dash
01-osh
01-osh
01-bash-4.4
...
"""
from __future__ import print_function

import collections
import optparse
import os
import re
import sys


def log(msg, *args):
    if args:
        msg = msg % args
    print(msg, file=sys.stderr)


def Cell(i):
    """Visually show number of processes.

    ^  ^^  ^^^  etc.
    """
    s = '^' * i
    return '%6s' % s


# lines look like this:
#
# 554  01-osh.1234
# 553  01-osh.1235

WC_LINE = re.compile(
    r'''
\s*  
(\d+)     # number of lines
\s+
([a-z0-9.-]+)  # shell name, could be bash-4.4
__
(\d{2})   # case ID
''', re.VERBOSE)

assert WC_LINE.match('    68 osh-cpp__01.19610')
# This is unfortunate
assert WC_LINE.match('    68 bash-4.4__01.19610')


def WriteHeader(f, shells, col=''):
    f.write("ID\t")
    for sh in shells:
        # abbreviate
        if sh.startswith('bash-4'):
            sh = 'bash-4'
        elif sh.startswith('bash-5'):
            sh = 'bash-5'
        f.write("%6s\t" % sh)
    f.write('%s\t' % col)
    f.write('Description')
    f.write("\n")


def WriteProcessReport(f, cases, code_strs, proc_sh, num_procs,
                       procs_by_shell):
    not_minimum = 0
    more_than_bash = 0
    fewer_than_bash = 0

    minimum = {}  # case -> number of procses
    for case_id in sorted(cases):
        min_procs = 20
        for sh in proc_sh:
            n = num_procs[case_id, sh]
            min_procs = min(n, min_procs)
        minimum[case_id] = min_procs

        osh_count = num_procs[case_id, 'osh']
        if osh_count != min_procs:
            not_minimum += 1

        bash_count = num_procs[case_id, 'bash-5.2.21']
        if osh_count > bash_count:
            more_than_bash += 1
        if osh_count < bash_count:
            fewer_than_bash += 1

    f.write('Number of Processes Started, by shell and test case\n')
    f.write('\n')
    f.write("Cases where ...\n")
    f.write("  OSH isn't the minimum: %d\n" % not_minimum)
    f.write("  OSH starts more than bash 5: %d\n" % more_than_bash)
    f.write("  OSH starts fewer than bash 5: %d\n\n" % fewer_than_bash)
    f.write('\n')
    WriteHeader(f, proc_sh, col='osh>min')
    f.write('\n')

    f.write("TOTAL\t")
    for sh in proc_sh:
        f.write('%6d\t' % procs_by_shell[sh])
    f.write('\n')
    f.write('\n')

    for case_id in sorted(cases):
        f.write(case_id + "\t")
        for sh in proc_sh:
            n = num_procs[case_id, sh]
            f.write(Cell(n) + "\t")

        osh_count = num_procs[case_id, 'osh']
        min_procs = minimum[case_id]
        if osh_count != min_procs:
            f.write('%d>%d\t' % (osh_count, min_procs))
        else:
            f.write('\t')

        f.write(code_strs[case_id])
        f.write("\n")

    return not_minimum, more_than_bash, fewer_than_bash


def WriteSyscallReport(f, cases, code_strs, syscall_sh, num_syscalls,
                       syscalls_by_shell):
    f.write('Number of Syscalls\n\n')

    WriteHeader(f, syscall_sh)

    for case_id in sorted(cases):
        f.write(case_id + "\t")
        #min_procs = 20
        for sh in syscall_sh:
            n = num_syscalls[case_id, sh]
            f.write('%6d\t' % n)
            #min_procs = min(n, min_procs)

        f.write('\t')

        f.write(code_strs[case_id])
        f.write("\n")

    f.write("TOTAL\t")
    for sh in syscall_sh:
        f.write('%6d\t' % syscalls_by_shell[sh])
    f.write('\n\n')


def Options():
    """Returns an option parser instance."""
    p = optparse.OptionParser()
    p.add_option('--suite',
                 dest='suite',
                 default='SUITE',
                 help='Test suite name')
    p.add_option(
        '--not-minimum',
        dest='not_minimum',
        type=int,
        default=0,
        help=
        "Expected number of cases where OSH doesn't start the minimum number of"
        "processes")
    p.add_option(
        '--more-than-bash',
        dest='more_than_bash',
        type=int,
        default=0,
        help=
        'Expected number of cases where OSH starts more processes than bash')
    return p


def main(argv):
    o = Options()
    opts, argv = o.parse_args(argv[1:])

    cases_path = argv[0]
    out_dir = argv[1]

    code_strs = {}
    with open(cases_path) as f:
        for line in f:
            case_id, code_str = line.split(None, 1)  # whitespace
            code_strs[case_id] = code_str

    cases = set()
    shells = set()

    num_procs = collections.defaultdict(int)
    procs_by_shell = collections.defaultdict(int)

    num_syscalls = collections.defaultdict(int)
    syscalls_by_shell = collections.defaultdict(int)

    #
    # Summarize Data
    #

    for line in sys.stdin:
        m = WC_LINE.match(line)
        if not m:
            raise RuntimeError('Invalid line %r' % line)
        num_sys, sh, case = m.groups()
        num_sys = int(num_sys)

        cases.add(case)
        shells.add(sh)

        num_procs[case, sh] += 1
        num_syscalls[case, sh] += num_sys

        procs_by_shell[sh] += 1
        syscalls_by_shell[sh] += num_sys

    # Orders columns by how good the results are, then shell name.
    proc_sh = sorted(procs_by_shell, key=lambda sh: (procs_by_shell[sh], sh))
    syscall_sh = sorted(syscalls_by_shell,
                        key=lambda sh: (syscalls_by_shell[sh], sh))

    #
    # Print Tables
    #

    out_path = os.path.join(out_dir, 'processes.%s.txt' % opts.suite)
    with open(out_path, 'w') as f:
        not_minimum, more_than_bash, fewer_than_bash = WriteProcessReport(
            f, cases, code_strs, proc_sh, num_procs, procs_by_shell)
    log('Wrote %s', out_path)

    #
    # Print Table of Syscall Counts
    #

    out_path = os.path.join(out_dir, 'syscalls.%s.txt' % opts.suite)
    with open(out_path, 'w') as f:
        WriteSyscallReport(f, cases, code_strs, syscall_sh, num_syscalls,
                           syscalls_by_shell)
    log('Wrote %s', out_path)

    ok = True
    if more_than_bash != opts.more_than_bash:
        log('Expected %d more than bash, got %d', opts.more_than_bash,
            more_than_bash)
        ok = False

    if not_minimum != opts.not_minimum:
        log('Expected %d that are not minimal, got %d', opts.not_minimum,
            not_minimum)
        ok = False

    return 0 if ok else 1


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
