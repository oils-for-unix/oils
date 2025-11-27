#!/usr/bin/env python3
"""
stat_log.py - Save portions of /proc/{stat,vmstat,meminfo,diskstas}

Runs in an infinite loop, until SIGTERM
"""
import optparse
import os
import signal
import sys
import time


def log(msg, *args):
    if args:
        msg = msg % args
    print(msg, file=sys.stderr)


def Options():
    """Returns an option parser instance."""

    p = optparse.OptionParser()

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
o_mem = None
o_disk = None


def FlushAll():
    o_stat.flush()
    o_vm.flush()
    o_mem.flush()
    o_disk.flush()


def Handler(signum, frame):
    log('[%s] Received SIGTERM, flushing logs and exiting ...', sys.argv[0])
    FlushAll()
    sys.exit(0)


def main(argv):
    o = Options()
    opts, argv = o.parse_args(argv)

    # Saving lines
    stat_filename = os.path.join(opts.out_dir, 'stat.txt')
    vmstat_filename = os.path.join(opts.out_dir, 'vmstat.txt')
    meminfo_filename = os.path.join(opts.out_dir, 'meminfo.txt')
    diskstats_filename = os.path.join(opts.out_dir, 'diskstats.txt')

    log('[%s] Saving to files in %s every %d seconds', sys.argv[0],
        opts.out_dir, opts.sleep_secs)

    global o_stat, o_vm, o_mem, o_disk  # flushed by signal handler

    o_stat = open(stat_filename, 'w')
    o_vm = open(vmstat_filename, 'w')
    o_mem = open(meminfo_filename, 'w')
    o_disk = open(diskstats_filename, 'w')

    signal.signal(signal.SIGTERM, Handler)

    i = 0
    while True:
        t = int(time.time())  # truncate to nearest second, to save space
        #print(t)

        with open('/proc/stat') as f:
            for line in f:
                # context switches
                if line.startswith('cpu') or line.startswith('ctx'):
                    #log('line %r', line)
                    o_stat.write('%s %s' % (t, line))

        with open('/proc/vmstat') as f:
            for line in f:
                # pgpgin and pgpgout are paging operations
                if (line.startswith('pgfault') or
                        line.startswith('pgmajfault') or
                        line.startswith('pgpg')):
                    #log('line %r', line)
                    o_vm.write('%s %s' % (t, line))

        with open('/proc/meminfo') as f:
            for line in f:
                if 'Total' in line:  # MemTotal and SwapTotal never change
                    continue
                if line.startswith('Mem') or line.startswith('Swap'):
                    #log('line %r', line)
                    o_mem.write('%s %s' % (t, line))

        with open('/proc/diskstats') as f:
            for line in f:
                if 'loop' in line:  # ignore loopback devices
                    continue
                o_disk.write('%s %s' % (t, line))

        # So we can tail -f
        if i % 10 == 0:
            FlushAll()

        time.sleep(opts.sleep_secs)
        i += 1

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
