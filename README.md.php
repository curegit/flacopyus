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

### Sync

```txt
<?= shell_exec("python3 -m flacopyus sync --help") ?>
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
