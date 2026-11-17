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
operations keep working.

`git sparse-checkout set` alone can refuse to remove worktree files it
considers "not up to date" (for example when a global git filter such as
git-lfs rewrote files during the clone, or when stat information went
stale while PlatformIO moved the package directory). This script therefore
forces the skip-worktree bits for every excluded path and removes any
leftovers from the working tree afterwards. For non-git installations
(registry tarball) the files are deleted directly; for registry installs
the same paths are already excluded from the tarball, so the script is
mostly a no-op safety net.
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

# git pathspecs of everything that must disappear
PRUNE_PATHSPECS = PRUNE_DIRS + PRUNE_GLOBS


def is_git_repo():
    return os.path.isfile(os.path.join(SDK_DIR, ".git")) or os.path.isdir(
        os.path.join(SDK_DIR, ".git")
    )


def git(args, check=True, feed=None):
    cmd = ["git", "-C", SDK_DIR] + args
    return subprocess.run(
        cmd, capture_output=True, text=True, check=check, input=feed
    )


def prune_size():
    total = 0
    for dirpath, _, filenames in os.walk(SDK_DIR, followlinks=False):
        for f in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total


def list_tracked_pruned_paths():
    """Tracked files inside the prune scope, tagged H (worktree) or
    S (already skip-worktree)."""
    result = git(["ls-files", "-t", "-z", "--"] + PRUNE_PATHSPECS)
    paths = []
    for entry in result.stdout.split("\0"):
        if not entry:
            continue
        # format: "<TAG> <path>"
        tag, path = entry[:1], entry[2:]
        if tag == "H":
            paths.append(path)
    return paths


def force_skip_worktree(paths):
    if not paths:
        return
    git(
        ["update-index", "--skip-worktree", "-z", "--stdin"],
        feed="".join("%s\0" % p for p in paths),
    )
    print("Marked %d tracked files as skip-worktree" % len(paths))


def prune_with_git():
    """Configure git sparse-checkout and force it onto the working tree."""
    if not is_git_repo():
        return False

    result = git(["sparse-checkout", "set", "--no-cone"] + SPARSE_PATTERNS)
    if result.returncode != 0:
        print(
            "Warning: git sparse-checkout failed (%s); falling back to deletion"
            % result.stderr.strip()
        )
        return False
    print("Configured git sparse-checkout for the mspm0-sdk submodule")

    # Remove any leftovers that sparse-checkout refused to touch
    # ("not up to date" worktree files)
    try:
        force_skip_worktree(list_tracked_pruned_paths())
    except subprocess.CalledProcessError as exc:
        print("Warning: could not set skip-worktree bits (%s)" % exc)
    return True


def prune_with_delete():
    """Plain deletion for non-git installs (and leftovers from prune_with_git)."""
    for rel_dir in PRUNE_DIRS:
        target = os.path.join(SDK_DIR, rel_dir)
        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)
    for pattern in PRUNE_GLOBS:
        for target in glob.glob(os.path.join(SDK_DIR, pattern)):
            if os.path.isfile(target):
                os.remove(target)


def main():
    if not os.path.isdir(SDK_DIR):
        print("Nothing to prune (no mspm0-sdk directory)")
        return 0
    before = prune_size()
    if is_git_repo():
        if not prune_with_git():
            prune_with_delete()
    # Always sweep leftovers (also a no-op for already-pruned tarballs)
    prune_with_delete()
    after = prune_size()
    print(
        "Pruned %.1f MB (%.1f MB remain)"
        % ((before - after) / 1024 / 1024, after / 1024 / 1024)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
