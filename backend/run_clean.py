#!/usr/bin/env python3
"""
Clean runner for uv commands without VIRTUAL_ENV warnings.

This script temporarily unsets VIRTUAL_ENV to avoid conflicts with uv.
"""

import os
import subprocess
import sys


def run_uv_clean(*args):
    """Run uv command with clean environment (no VIRTUAL_ENV)."""
    # Create a copy of the environment without VIRTUAL_ENV
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)

    # Run the uv command
    cmd = ["uv"] + list(args)
    result = subprocess.run(cmd, env=env)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_clean.py <uv_command> [args...]")
        print("Example: python run_clean.py run python -c 'import httpx'")
        sys.exit(1)

    # Pass all arguments except the script name to uv
    exit_code = run_uv_clean(*sys.argv[1:])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
