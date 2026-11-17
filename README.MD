# toolchain-timspm0-sdk

Texas Instruments MSPM0 SDK packaged for the [timspm0 PlatformIO platform](https://github.com/Berkays/platform-ti-mspm0).

The MSPM0 SDK fully belongs to Texas Instruments; use of this package is
subject to the TI Software License Agreement shipped inside the package
(`mspm0-sdk/license_mspm0_sdk_*.txt`) and at
<https://www.ti.com/tool/MSPM0-SDK>.

## Structure

The SDK lives in the `mspm0-sdk` git submodule pointing at a release tag of
<https://github.com/TexasInstruments/mspm0-sdk>.

To keep installations lean, content the timspm0 platform cannot use is
pruned on install (via the `scripts/prune.py` post-install script) and
excluded from registry tarballs (via `export.exclude`):

- `docs/`, `examples/`, `tools/` and the root-level `*.html` documents
  (with all documentation images)
- prebuilt libraries, startup and linker files for non-GCC toolchains
  (IAR, Keil, TI Clang) - the platform builds with GCC only
- MSPS series device support files (startup/linker scripts) - the platform
  targets MSPM0 MCUs only

For git installs the prune uses `git sparse-checkout` inside the submodule,
so `pio pkg update` keeps working and future SDK releases stay pruned
automatically. A full SDK checkout is ~2 GB; pruned it is ~160 MB (~40 MB
as a registry tarball). If you need the removed content (e.g. IAR/Keil
support or the SDK examples), use TI's upstream repository directly.

## Versioning

TI releases have 4-component versions (e.g. `2.08.00.03`, tag
`mspm0_sdk_2_08_00_03`). The PlatformIO package version is derived as
`<major>.<minor>.<patch>+<build>`:

| TI version  | Tag                    | Package version |
| ----------- | ---------------------- | --------------- |
| 2.08.00.03  | `mspm0_sdk_2_08_00_03` | `2.8.0+3`       |
| 2.11.00.07  | `mspm0_sdk_2_11_00_07` | `2.11.0+7`      |

## Updating to a new TI release

Use the helper script in the platform repository:

```console
$ git clone https://github.com/Berkays/platform-ti-mspm0
$ python3 platform-ti-mspm0/scripts/update_sdk.py          # list releases
$ python3 platform-ti-mspm0/scripts/update_sdk.py --latest # bump + publish
```

The script updates the submodule to the chosen TI tag, rewrites the package
version, commits, tags, pushes and (optionally) publishes to the registry.
