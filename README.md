# Flacopyus

Mirror your FLAC audio library to a portable lossy Opus version

![data flow animation of Flacopyus](images/FlacopyusFlow.png)

```sh
# Encodes a FLAC library to Opus and mirrors them together with MP3 and M4A files
flacopyus sync FLAC/ OPUS/ -P --bitrate 128 --delete-excluded --copy mp3 m4a
```

## Motivation

Lossless audio libraries are often too large for mobile devices or cloud storage, so having a compact, portable duplicate is desirable.

Flacopyus is a CLI tool that mirrors your lossless FLAC library to a portable Opus collection.
It performs rsync-like batch mirroring with incremental encoding/copying to save time.
It preserves metadata and is idempotent, so repeated runs safely keep the destination in sync.

We specifically target FLAC to Opus because both formats use Vorbis Comment, meaning it transparently preserves nearly all metadata, including album art.

## How It Works

- Uses the `opusenc` binary; works on any OS where `opusenc` is available.
- Copies the source file modification time to the encoded Opus file.
- Incrementally encodes new files and updates Opus files when modification times differ.
- Able to copy additional formats (e.g., `mp3`, `m4a`) to support mixed lossless/lossy libraries.

## Installation

Python 3.14 or later is required.

```sh
pip install flacopyus
```

`opusenc` binary is included in the package only for Windows.
For other platforms, please install it manually and add it to the `PATH` environment variable, or use the appropriate package manager.

### Homebrew (macOS)

```sh
brew install opus-tools
```

### Debian/Ubuntu

```sh
apt install opus-tools
```

## Usage

The program is invoked either through `flacopyus` command, or via the Python main module option: `python3 -m flacopyus`.

### Sync

The main operation is the `sync` command, which creates a lossy Opus version of your FLAC audio library.
Consider using the `-P` option for large libraries to speed up the process by encoding in parallel.

```txt
usage: flacopyus sync [-h] [-v] [-f] [--opusenc EXE | --prefer-external]
                      [-b KBPS] [--vbr | --cbr | --hard-cbr] [--music |
                      --speech] [--downmix-mono | --downmix-stereo]
                      [--re-encode] [--wav] [--aiff] [-c EXT [EXT ...]]
                      [--modtime-window SECONDS] [--checksum] [--delete |
                      --delete-excluded] [--delete-dir | --purge-dir]
                      [--fix-case] [-P [THREADS]] [--allow-parallel-io]
                      [--parallel-copy THREADS]
                      SRC DEST

Mirror your FLAC audio library to a portable lossy Opus version

positional arguments:
  SRC                   source directory containing FLAC files
  DEST                  destination directory saving Opus files

options:
  -h, --help            show this help message and exit
  -v, --verbose         verbose output (default: False)
  -f, --force           disable safety checks and force continuing (default:
                        False)
  --opusenc EXE         specify an opusenc executable binary to use (default:
                        None)
  --prefer-external     prefer an external binary instead of the internal one
                        (effectively Windows-only option) (default: False)

Opus encoding options:
  Note that changing these options will NOT trigger re-encoding of existing
  Opus files so that the change will affect incrementally. Use '--re-encode'
  to recreate all Opus files.

  -b, --bitrate KBPS    target bitrate in kbps of Opus files (integer in
                        6-256) (default: 128)
  --vbr                 use Opus variable bitrate mode (default: --vbr)
  --cbr                 use Opus constrained variable bitrate mode
  --hard-cbr            use Opus hard constant bitrate mode
  --music               force Opus encoder to tune low bitrates for music
                        (default: False)
  --speech              force Opus encoder to tune low bitrates for speech
                        (default: False)
  --downmix-mono        downmix to mono (default: False)
  --downmix-stereo      downmix to stereo (if having more than 2 channels)
                        (default: False)

mirroring options:
  --re-encode           force re-encoding of all Opus files (default: False)
  --wav                 also encode WAV files (.wav extension) to Opus files
                        (default: False)
  --aiff                also encode AIFF files (.aif/.aiff extension) to Opus
                        files (default: False)
  -c, --copy EXT [EXT ...]
                        copy files whose extension is .EXT (case-insensitive)
                        from SRC to DEST (default: None)
  --modtime-window SECONDS
                        modification time window in seconds which is used to
                        determine if a file is updated (default requires exact
                        modification time match) (default: 0.0)
  --checksum            use checksum to determine if a file is need to copy
                        instead of modification time-based comparison
                        (default: False)
  --delete              delete files with relevant extensions in DEST that are
                        not in SRC (default: False)
  --delete-excluded     delete any files in DEST that are not in SRC (default:
                        False)
  --delete-dir          delete empty directories in DEST that are not in SRC
                        (default: False)
  --purge-dir           delete all empty directories in DEST (default: False)
  --fix-case            fix file/directory name cases to match the source
                        directory (for filesystem environments that are case-
                        insensitive) (default: False)

concurrency options:
  -P, --parallel-encoding [THREADS]
                        enable parallel encoding with THREADS threads [THREADS
                        = max(1, #CPUcores - 1)] (default: None)
  --allow-parallel-io   disable mutual exclusion for disk I/O operations
                        during parallel encoding (not recommended for Hard
                        Disk drives) (default: False)
  --parallel-copy THREADS
                        concurrency of copy operations (default: 1)

A '--' is usable to terminate option parsing so remaining arguments are
treated as positional arguments.
```

### Test

`test` command is used to test the Opus encoder setup.
It checks if the `opusenc` binary is available and if it can encode test streams without errors.

```txt
usage: flacopyus test [-h] [-v] [--opusenc EXE | --prefer-external]

Examine Opus encoder setup and test encode functionality

options:
  -h, --help         show this help message and exit
  -v, --verbose      verbose output (default: False)
  --opusenc EXE      specify an opusenc executable binary to use (default:
                     None)
  --prefer-external  prefer an external binary instead of the internal one
                     (effectively Windows-only option) (default: False)
```

## Limitations

- Syncing across filesystem environments which have different naming case sensitivity may cause unexpected behavior; file names may conflict in the destination directory, stale files may be left in the destination directory.
- It follows symlinks and handles its contents in the source directory, but does not transfer them as links to the destination directory.

## Notice Regarding Bundled Binaries

This distribution includes prebuilt `opusenc` binary for Windows (x86/x64) from [the Opus-tools project](https://opus-codec.org/downloads/).
These binaries are provided unmodified and are used as external utilities for Windows.

### Opus-tools License

Opus-tools, with the exception of `opusinfo` is available under the following two clause BSD-style license:

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

- Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

```txt
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER
OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

## Flacopyus License

GNU General Public License v3.0 or later

Copyright (C) 2025 curegit

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.
If not, see <https://www.gnu.org/licenses/>.
