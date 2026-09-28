#!/usr/bin/env python3
"""Run a Python script and log its combined stdout/stderr to output.txt (overwrite each run).
Usage: python run_and_log.py path/to/script.py [args...]
"""
import sys
from pathlib import Path
import subprocess


def main():
    if len(sys.argv) < 2:
        print("Usage: run_and_log.py <script.py> [args...]")
        return 2
    script = Path(sys.argv[1])
    if not script.exists():
        print(f"Script not found: {script}", file=sys.stderr)
        return 3
    args = sys.argv[2:]
    out_path = Path("output.txt")
    # Open output file in write mode - overwrites each run
    with out_path.open("w", encoding="utf-8") as outf:
        cmd = [sys.executable, "-u", str(script)] + args
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        if proc.stdout is None:
            proc.wait()
            return proc.returncode
        try:
            for line in proc.stdout:
                outf.write(line)
                outf.flush()
                sys.stdout.write(line)
                sys.stdout.flush()
        except KeyboardInterrupt:
            proc.kill()
            proc.wait()
            raise
        return proc.wait()


if __name__ == "__main__":
    raise SystemExit(main())
