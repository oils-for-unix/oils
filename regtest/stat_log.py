#!/usr/bin/env python3
"""
stat_log.py - Save portions of /proc/stat and /proc/vmstat

Runs in an infinite loop, until SIGTERM
"""
import optparse
import os
import signal
import sys
import time


def log(msg: str, *args) -> None:
    if args:
        msg = msg % args
    #print('%.2f %s' % (time.time() - START_TIME, msg), file=sys.stderr)
    print(msg, file=sys.stderr)


def Options() -> optparse.OptionParser:
    """Returns an option parser instance."""

    p = optparse.OptionParser()
    p.add_option('-v',
                 '--verbose',
                 dest='verbose',
                 action='store_true',
                 default=False,
                 help='Show details about translation')

    # Control which modules are exported to the header.  Used by
    # build/translate.sh.
    p.add_option('--out-dir',
                 dest='out_dir',
                 default='_tmp',
                 help='Write files to this directory')

    p.add_option('--sleep-secs',
                 dest='sleep_secs',
                 type='int',
                 default=1,
                 help='Seconds to sleep')

    return p


o_stat = None
o_vm = None


def Handler(signum, frame):
    log('[%s] Received SIGTERM, flushing logs and exiting ...', sys.argv[0])
    o_stat.flush()
    o_vm.flush()
    sys.exit(0)


def main(argv: list[str]) -> int:
    o = Options()
    opts, argv = o.parse_args(argv)

    # Saving lines
    stat_filename = os.path.join(opts.out_dir, 'stat.txt')
    vmstat_filename = os.path.join(opts.out_dir, 'vmstat.txt')

    log('[%s] Saving to %s, %s every %d seconds', sys.argv[0], stat_filename,
        vmstat_filename, opts.sleep_secs)

    global o_stat, o_vm  # flushed by signal handler

    o_stat = open(stat_filename, 'w')
    o_vm = open(vmstat_filename, 'w')

    signal.signal(signal.SIGTERM, Handler)

    i = 0
    while True:
        t = int(time.time())  # truncate to nearest second, to save space
        #print(t)

        with open('/proc/stat') as i_stat:
            for line in i_stat:
                # context switches
                if line.startswith('cpu') or line.startswith('ctx'):
                    #log('line %r', line)
                    o_stat.write('%s %s' % (t, line))

        with open('/proc/vmstat') as i_stat:
            for line in i_stat:
                # context switches
                if line.startswith('pgfault') or line.startswith('pgmajfault'):
                    #log('line %r', line)
                    o_vm.write('%s %s' % (t, line))

        time.sleep(opts.sleep_secs)

        # So we can tail -f
        if i % 10 == 0:
            o_stat.flush()
            o_vm.flush()

        i += 1

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
