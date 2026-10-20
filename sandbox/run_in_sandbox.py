#!/usr/bin/env python3
"""Run fleet-audit's tests and evals inside an E2B sandbox (a Firecracker microVM), away from your own machine.

  python3 sandbox/run_in_sandbox.py                 say where the evals run in isolation today, and exit 0
  uv run --with e2b python3 sandbox/run_in_sandbox.py --boot
                                                    boot a sandbox, install this checkout, run the evals in it

Booting is a billed call, so it happens only with --boot and an E2B_API_KEY in the environment. The checkout goes
in as a `git archive` of HEAD, so a private repository needs no token inside the sandbox. Without --boot, the
isolation is the CI runner: a fresh virtual machine for every push (.github/workflows/ci.yml).
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    "mkdir -p /home/user/fleet-audit && tar -xzf /home/user/fleet-audit.tar.gz -C /home/user/fleet-audit",
    "python3 -m venv /home/user/venv && /home/user/venv/bin/pip install --quiet /home/user/fleet-audit",
    "/home/user/venv/bin/fleet-audit --version",
    "cd /home/user/fleet-audit && /home/user/venv/bin/python -m unittest",
    "cd /home/user/fleet-audit && /home/user/venv/bin/python evals/run.py",
]


def main() -> int:
    if {"-h", "--help"} & set(sys.argv[1:]):
        print(__doc__)
        return 0
    if "--boot" not in sys.argv or not os.environ.get("E2B_API_KEY"):
        print("isolation today: the CI runner, a fresh virtual machine per push (.github/workflows/ci.yml).\n"
              "an E2B boot needs --boot and E2B_API_KEY (a billed call); nothing was booted.")
        return 0
    from e2b import CommandExitException, Sandbox  # imported here so the dry path needs no package

    archive = subprocess.run(["git", "archive", "--format=tar.gz", "HEAD"], cwd=ROOT, capture_output=True, check=True)
    started = time.monotonic()
    sbx = Sandbox.create(timeout=600)
    print(f"sandbox {sbx.sandbox_id} up in {time.monotonic() - started:.2f}s")
    try:
        sbx.files.write("/home/user/fleet-audit.tar.gz", io.BytesIO(archive.stdout))
        for step in STEPS:
            t = time.monotonic()
            try:
                result = sbx.commands.run(step, timeout=300)
            except CommandExitException as err:
                print(f"FAIL ({err.exit_code}) {step}\n{err.stdout[-2000:]}{err.stderr[-2000:]}")
                return 1
            print(f"ok {time.monotonic() - t:6.1f}s  {step}")
            if result.stdout.strip():
                print("   " + result.stdout.strip().splitlines()[-1])
        return 0
    finally:
        sbx.kill()


if __name__ == "__main__":
    raise SystemExit(main())
