import io
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from rich.console import Console
from flacopyus.assets import get_test_streams
from flacopyus.filesys import temporary_directory, temporary_file
from flacopyus.main import main


@contextmanager
def _quiet():
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, no_color=True)
    with patch("flacopyus.main.error_console", console), patch("flacopyus.stdio.error_console", console):
        yield buf


def _library(stack: ExitStack) -> tuple[Path, Path, Path]:
    # Zip resources are extracted as separate temp files, so their parent is not a library.
    src = stack.enter_context(temporary_directory())
    linked: dict[str, Path] = {}
    for stream in get_test_streams():
        path = stack.enter_context(stream)
        link = src / path.name
        link.symlink_to(path)
        linked[path.suffix.lower()] = link
    return src, linked[".flac"], linked[".wav"]


def _write(stack: ExitStack, parent: Path, suffix: str, data: bytes) -> Path:
    fp, path = stack.enter_context(temporary_file(parent=parent, suffix=suffix))
    fp.write(data)
    fp.flush()
    return path


class MainTest(TestCase):
    def test_encodes_flac_and_skips_unchanged(self):
        with ExitStack() as stack:
            src, flac, wav = _library(stack)
            dest = stack.enter_context(temporary_directory())
            opus = (dest / flac.name).with_suffix(".opus")

            with _quiet() as output:
                self.assertEqual(main(src, dest), 0)
            self.assertIn("1 files encoded, 0 files already up-to-date", output.getvalue())
            self.assertEqual(opus.read_bytes()[:4], b"OggS")
            self.assertFalse((dest / wav.name).exists())
            self.assertFalse((dest / wav.name).with_suffix(".opus").exists())

            with _quiet() as output:
                self.assertEqual(main(src, dest), 0)
            self.assertIn("0 files encoded, 1 files already up-to-date", output.getvalue())

            with _quiet() as output:
                self.assertEqual(main(src, dest, re_encode=True), 0)
            self.assertIn("1 files encoded, 0 files already up-to-date", output.getvalue())
            self.assertEqual(opus.read_bytes()[:4], b"OggS")

    def test_copies_extension(self):
        with ExitStack() as stack:
            src, flac, wav = _library(stack)
            dest = stack.enter_context(temporary_directory())

            with _quiet() as output:
                self.assertEqual(main(src, dest, copy_exts=["WAV"]), 0)
            text = output.getvalue()
            self.assertIn("1 files encoded, 0 files already up-to-date", text)
            self.assertIn("1 files copied, 0 files already up-to-date", text)
            self.assertEqual((dest / flac.name).with_suffix(".opus").read_bytes()[:4], b"OggS")
            self.assertEqual((dest / wav.name).read_bytes(), wav.read_bytes())

            with _quiet() as output:
                self.assertEqual(main(src, dest, copy_exts=["wav"]), 0)
            text = output.getvalue()
            self.assertIn("0 files encoded, 1 files already up-to-date", text)
            self.assertIn("0 files copied, 1 files already up-to-date", text)

    def test_deletes_stale_files_and_directories(self):
        with ExitStack() as stack:
            src, flac, _ = _library(stack)
            dest = stack.enter_context(temporary_directory())
            with _quiet():
                self.assertEqual(main(src, dest), 0)

            opus = (dest / flac.name).with_suffix(".opus")
            stale = _write(stack, dest, ".opus", b"stale")
            kept = _write(stack, dest, ".txt", b"note")
            empty = dest / "empty"
            empty.mkdir()

            with _quiet() as output:
                self.assertEqual(main(src, dest, delete=True, delete_dir=True), 0)
            self.assertIn("1 files deleted", output.getvalue())
            self.assertTrue(opus.is_file())
            self.assertFalse(stale.exists())
            self.assertEqual(kept.read_bytes(), b"note")
            self.assertFalse(empty.exists())

            with _quiet() as output:
                self.assertEqual(main(src, dest, delete_excluded=True), 0)
            self.assertIn("1 files deleted", output.getvalue())
            self.assertTrue(opus.is_file())
            self.assertFalse(kept.exists())

    def test_safety_checks(self):
        with temporary_directory() as root, temporary_directory() as dest, _quiet():
            with self.subTest(case="missing source"):
                with self.assertRaisesRegex(FileNotFoundError, "not a directory"):
                    main(root / "missing", dest)

            with self.subTest(case="source is file"):
                with temporary_file() as (_, path):
                    with self.assertRaisesRegex(FileNotFoundError, "not a directory"):
                        main(path, dest)

            with self.subTest(case="no audio"):
                with temporary_directory() as src:
                    with self.assertRaisesRegex(RuntimeError, "No flac"):
                        main(src, dest)

            with self.subTest(case="destination inside source"):
                with temporary_directory() as src:
                    nested = src / "dest"
                    nested.mkdir()
                    with self.assertRaisesRegex(RuntimeError, "inside"):
                        main(src, nested)

            nested = dest / "library"
            nested.mkdir()
            with self.subTest(case="source inside destination"):
                with self.assertRaisesRegex(RuntimeError, "inside"):
                    main(nested, dest)

            with self.subTest(case="force"):
                self.assertEqual(main(nested, dest, force=True), 0)

            with self.subTest(case="copy encoded extension"):
                with self.assertRaisesRegex(ValueError, "Unable to copy"):
                    main(root, dest, copy_exts=["FLAC"])
                with self.assertRaisesRegex(ValueError, "Unable to copy"):
                    main(root, dest, wav=True, copy_exts=["wav"])
