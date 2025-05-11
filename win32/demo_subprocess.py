#!/usr/bin/env python3
"""
Testing child process APIs on Windows
"""

import subprocess
import sys


def RunPipeline(argv1, argv2, argv3):
    p1 = subprocess.Popen(argv1, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(argv2, stdin=p1.stdout, stdout=subprocess.PIPE)

    p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits

    p3 = subprocess.Popen(argv3, stdin=p2.stdout)
    p2.stdout.close()  # Allow p2 to receive a SIGPIPE if p3 exits

    # Wait for each process to complete and get exit codes
    c1 = p1.wait()
    c2 = p2.wait()
    c3 = p3.wait()
    return [c1, c2, c3]


def SubprocessDemo():
    if sys.platform == 'win32':
        # find /c /v is like wc -l
        #a_list = [['dir', 'build'], ['find', 'sh'], ['find', '/c', '/v', '""']]
        a_list = [['dir', 'build'], ['find', 'sh'], ['find', 'o']]

        a_list2 = []
        for a in a_list:
            a_list2.append(['cmd.exe', '/c'] + a)
        print(a_list2)

        codes = RunPipeline(a_list2[0], a_list2[1], a_list2[2])
        print(codes)
        return

    codes = RunPipeline(['ls', 'build'], ['grep', 'sh'], ['grep', 'o'])
    print(codes)

    codes = RunPipeline(['ls', 'build'], ['sh', '-c', 'grep py; exit 42'],
                        ['wc', '-l'])
    print(codes)


SubprocessDemo()
