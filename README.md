# Flacopyus

Mirror your FLAC audio library to a portable lossy Opus version

```sh
flacopyus sync FLAC/ OPUS/ -P --bitrate 128 --delete-excluded --copy mp3 m4a
```

## Motivation

Lossless audio libraries are often too large for mobile devices or cloud storage, so having a compact, portable duplicate is desirable.

Flacopyus mirrors your lossless FLAC library to a portable Opus collection.
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

Currently, `opusenc` binary is included in the package only for Windows (x86/x64).
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

### Sync

The main operation is the `sync` command, which creates a lossy Opus version of your FLAC audio library.
Consider using the `-P` option for large libraries to speed up the process by encoding in parallel.

```txt
usage: flacopyus sync [-h] [-v] [-f] [-b KBPS] [--vbr | --cbr | --hard-cbr]
                      [--music | --speech] [--downmix-mono | --downmix-stereo]
                      [--re-encode] [--wav] [-c EXT [EXT ...]] [--delete |
                      --delete-excluded] [--fix-case] [-P [THREADS]]
                      [--allow-parallel-io] [--parallel-copy THREADS]
                      SRC DEST

Mirror your FLAC audio library to a portable lossy Opus version

positional arguments:
  SRC                   source directory containing FLAC files
  DEST                  destination directory saving Opus files

options:
  -h, --help            show this help message and exit
  -v, --verbose         verbose output
  -f, --force           disable safety checks and force continuing

Opus encoding options:
  Note that changing these options will NOT trigger re-encoding of existing
  Opus files so that the change will affect incrementally. Use '--re-encode'
  to recreate all Opus files.

  -b, --bitrate KBPS    target bitrate in kbps of Opus files (integer in
                        6-256)
  --vbr                 use Opus variable bitrate mode
  --cbr                 use Opus constrained variable bitrate mode
  --hard-cbr            use Opus hard constant bitrate mode
  --music               force Opus encoder to tune low bitrates for music
  --speech              force Opus encoder to tune low bitrates for speech
  --downmix-mono        downmix to mono
  --downmix-stereo      downmix to stereo (if having more than 2 channels)

mirroring options:
  --re-encode           force re-encoding of all Opus files
  --wav                 also encode WAV files (.wav extension) to Opus files
  -c, --copy EXT [EXT ...]
                        copy files whose extension is .EXT (case-insensitive)
                        from SRC to DEST
  --delete              delete files with relevant extensions in DEST that are
                        not in SRC
  --delete-excluded     delete any files in DEST that are not in SRC
  --fix-case            fix file/directory name cases to match the source
                        directory (for filesystems that are case-insensitive)

concurrency options:
  -P, --parallel-encoding [THREADS]
                        enable parallel encoding with THREADS threads [THREADS
                        = max(1, #CPUcores - 1)]
  --allow-parallel-io   disable mutual exclusion for disk I/O operations
                        during parallel encoding (not recommended for Hard
                        Disk drives)
  --parallel-copy THREADS
                        concurrency of copy operations

A '--' is usable to terminate option parsing so remaining arguments are
treated as positional arguments.
```

### Test

`test` command is used to test the Opus encoder setup.
It checks if the `opusenc` binary is available and if it can encode a test stream without errors.

```txt
usage: flacopyus test [-h] [-v]

Examine Opus encoder setup

options:
  -h, --help     show this help message and exit
  -v, --verbose  verbose output
```

## Known Issues

- Requires a file system that supports nanosecond-precision modification times
- Limited support for symbolic links

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
