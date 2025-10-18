# Flacopyus

Mirror your FLAC audio library to a portable lossy Opus version

```sh
flacopyus FLAC/ OPUS/ --bitrate 128 --delete-excluded --copy mp3 m4a
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

Currently, `opusenc` is not included in the package.
Please install it manually and add it to the `PATH` environment variable.

## Usage

```txt
usage: flacopyus [-h] [-v] [-f] [-b KBPS] [--vbr | --cbr | --hard-cbr]
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
  -v, --version         show program's version number and exit
  -f, --force           disable safety checks and force continuing (default:
                        False)

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
  --wav                 also encode WAV files to Opus files (default: False)
  -c, --copy EXT [EXT ...]
                        copy files whose extension is .EXT (case-insensitive)
                        from SRC to DEST (default: None)
  --delete              delete files of relevant extensions in DEST that are
                        not in SRC (default: False)
  --delete-excluded     delete any files in DEST that are not in SRC (default:
                        False)
  --fix-case            fix file/directory name cases to match the source
                        directory (for filesystems that are case-insensitive)
                        (default: False)

concurrency options:
  -P, --parallel-encoding [THREADS]
                        enable parallel encoding with THREADS threads [THREADS
                        = max(1, number of CPU cores - 1)] (default: None)
  --allow-parallel-io   disable mutual exclusion for disk I/O operations
                        during parallel encoding (not recommended for Hard
                        Disk drives) (default: False)
  --parallel-copy THREADS
                        concurrency of copy operations (default: 1)

A '--' is usable to terminate option parsing so remaining arguments are
treated as positional arguments.
```

## Known Issues

- Requires a file system that supports nanosecond-precision modification times
- Limited support for symbolic links

## License

GNU General Public License v3.0 or later

Copyright (C) 2025 curegit

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.
If not, see <https://www.gnu.org/licenses/>.
