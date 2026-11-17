#!/usr/bin/env python3
"""Prune content that the timspm0 PlatformIO platform cannot use.

Runs as the package post-install script (with the package root as cwd).

Removed content:
  - docs/, examples/, tools/ and root-level *.html documents (with all
    documentation images) - not needed to build firmware
  - prebuilt libraries and startup/linker files for non-GCC toolchains
    (IAR, Keil, TI Clang) - this platform builds with GCC only
  - MSPS series device support files (startup + linker scripts) - the
    platform targets MSPM0 MCUs only

For git (VCS) installations this is implemented with `git sparse-checkout`
inside the mspm0-sdk submodule, so the excluded files are omitted in a
git-native way and future `pio pkg update` (git pull / submodule update)
operations keep working. For non-git installations (registry tarball) the
files are deleted directly; for registry installs the same paths are
already excluded from the tarball, so this is mostly a no-op safety net.
"""

import glob
import os
import shutil
import subprocess
import sys

SDK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mspm0-sdk")

# Directories removed entirely (paths relative to mspm0-sdk/)
PRUNE_DIRS = [
    # documentation (incl. images), examples, TI tools
    "docs",
    "examples",
    "tools",
    # prebuilt libraries for non-GCC toolchains
    "source/ti/driverlib/lib/iar",
    "source/ti/driverlib/lib/keil",
    "source/ti/driverlib/lib/ticlang",
    "source/ti/iqmath/lib/iar",
    "source/ti/iqmath/lib/keil",
    "source/ti/iqmath/lib/ticlang",
    # startup + linker files for non-GCC toolchains
    "source/ti/devices/msp/m0p/startup_system_files/iar",
    "source/ti/devices/msp/m0p/startup_system_files/keil",
    "source/ti/devices/msp/m0p/startup_system_files/ticlang",
    "source/ti/devices/msp/m0p/linker_files/iar",
    "source/ti/devices/msp/m0p/linker_files/keil",
    "source/ti/devices/msp/m0p/linker_files/ticlang",
]

# File globs removed (paths relative to mspm0-sdk/)
PRUNE_GLOBS = [
    # root-level documents (known issues FAQ, manifest, release notes)
    "*.html",
    # MSPS series (not MSPM0) device support files
    "source/ti/devices/msp/m0p/startup_system_files/gcc/startup_msps*",
    "source/ti/devices/msp/m0p/linker_files/gcc/msps*",
]

# git sparse-checkout patterns (gitignore-style, relative to mspm0-sdk/)
SPARSE_PATTERNS = ["/*"]
SPARSE_PATTERNS += ["!/%s/" % d for d in PRUNE_DIRS]
SPARSE_PATTERNS += ["!/%s" % g for g in PRUNE_GLOBS]


def prune_size():
    total = 0
    for dirpath, _, filenames in os.walk(SDK_DIR, followlinks=False):
        for f in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total


def prune_with_delete():
    """Plain deletion fallback for non-git installs."""
    for rel_dir in PRUNE_DIRS:
        target = os.path.join(SDK_DIR, rel_dir)
        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)
            print("Pruned %s" % rel_dir)
    for pattern in PRUNE_GLOBS:
        for target in glob.glob(os.path.join(SDK_DIR, pattern)):
            if os.path.isfile(target):
                os.remove(target)
                print("Pruned %s" % os.path.relpath(target, SDK_DIR))


def prune_with_sparse_checkout():
    """Configure git sparse-checkout inside the mspm0-sdk submodule.

    Keeps future `pio pkg update` (git pull --recurse-submodules) working:
    git itself omits the excluded paths instead of us deleting tracked
    files behind its back.
    """
    if not os.path.isfile(os.path.join(SDK_DIR, ".git")) and not os.path.isdir(
        os.path.join(SDK_DIR, ".git")
    ):
        return False
    cmd = ["git", "-C", SDK_DIR, "sparse-checkout", "set", "--no-cone"]
    cmd += SPARSE_PATTERNS
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(
            "Warning: git sparse-checkout failed (%s); falling back to deletion"
            % result.stderr.strip()
        )
        return False
    print("Configured git sparse-checkout for the mspm0-sdk submodule")
    return True


def main():
    if not os.path.isdir(SDK_DIR):
        print("Nothing to prune (no mspm0-sdk directory)")
        return 0
    before = prune_size()
    if not prune_with_sparse_checkout():
        prune_with_delete()
    after = prune_size()
    print(
        "Pruned %.1f MB (%.1f MB remain)"
        % ((before - after) / 1024 / 1024, after / 1024 / 1024)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
