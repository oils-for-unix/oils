#!/usr/bin/env python3
"""
Testing child process APIs on Windows
"""

import asyncio
import sys
import os
from typing import List


async def run_pipeline_async(commands: List[List[str]]) -> List[int]:
    """Run a pipeline of commands, letting stdout flow naturally, and return exit codes."""
    if not commands:
        return []

    exit_codes = []
    stdin = None  # Initial stdin is None (inherited)

    # Create pipes for connecting processes
    processes = []

    # Set up all processes in the pipeline
    for i, cmd in enumerate(commands):
        # For all processes except the last one, create a pipe for stdout
        if i < len(commands) - 1:
            # Create a pipe for this process's stdout to the next process's stdin
            read_fd, write_fd = os.pipe()
            stdout = write_fd
            next_stdin = read_fd
        else:
            # Last process inherits stdout (terminal or parent process stdout)
            stdout = None
            next_stdin = None

        # Create the process
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=stdin,
            stdout=stdout,
            stderr=None  # Inherit stderr
        )

        processes.append(proc)

        # Close write end of pipe in parent process after spawning child
        if i < len(commands) - 1:
            os.close(write_fd)

        # Set up for next iteration
        stdin = next_stdin

    # Wait for all processes to complete and collect exit codes
    for proc in processes:
        await proc.wait()
        exit_codes.append(proc.returncode)

    return exit_codes


def RunPipeline(*commands) -> List[int]:
    """Run a pipeline of commands with natural output flow and return exit codes."""
    return asyncio.run(run_pipeline_async(commands))


def SubprocessDemo():
    if sys.platform == 'win32':
        a_list = [['dir', 'build'], ['find', 'sh'], ['find', 'o']]

        a_list2 = []
        for a in a_list:
            a_list2.append(['cmd.exe', '/c'] + a)
        print(a_list2)

        #codes = RunPipeline(a_list2[0], a_list2[1], a_list2[2])
        exit_codes = RunPipeline(*a_list2)
        print(f"Exit codes: {exit_codes}")
        return

    # ls build | grep sh | wc -l
    exit_codes = RunPipeline(['ls', 'build'], ['grep', 'sh'], ['grep', 'o'])
    print(f"Exit codes: {exit_codes}")

    exit_codes = RunPipeline(['ls', 'build'], ['sh', '-c', 'grep py; exit 42'],
                             ['wc', '-l'])
    print(f"Exit codes: {exit_codes}")


# Example usage
if __name__ == "__main__":
    SubprocessDemo()
