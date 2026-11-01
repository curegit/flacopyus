import io
from contextlib import ExitStack
from pathlib import Path
from unittest import TestCase
from rich.console import Console
from flacopyus.filesys import itreemap, temporary_directory, temporary_file


def _write(stack: ExitStack, parent: Path, suffix: str, data: bytes) -> Path:
    fp, path = stack.enter_context(temporary_file(parent=parent, suffix=suffix))
    fp.write(data)
    fp.flush()
    return path


class ItreemapTest(TestCase):
    def test_maps_matching_files(self):
        def copy(src: Path, dest: Path) -> bytes:
            data = src.read_bytes()
            dest.write_bytes(data)
            return data

        with temporary_directory() as src, temporary_directory() as dest, ExitStack() as stack:
            (src / "empty").mkdir()
            album = src / "album"
            album.mkdir()
            flac = _write(stack, album, ".FLAC", b"audio")
            skipped = _write(stack, album, ".txt", b"text")
            cue = _write(stack, src, ".cue", b"cue")

            mapped = {src_path: (dest_path, data) for src_path, dest_path, data in itreemap(copy, src, dest, extmap={"flac": "opus", "cue": "cue"}, progress=False)}

            dest_flac = (dest / "album" / flac.name).with_suffix(".opus")
            self.assertEqual(mapped, {flac: (dest_flac, b"audio"), cue: (dest / cue.name, b"cue")})
            self.assertEqual(dest_flac.read_bytes(), b"audio")
            self.assertEqual((dest / cue.name).read_bytes(), b"cue")
            self.assertFalse((dest / "album" / skipped.name).exists())
            self.assertTrue((dest / "empty").is_dir())

    def test_copies_filtered_files(self):
        def convert(src: Path, dest: Path) -> None:
            dest.write_bytes(b"converted")

        with temporary_directory() as src, temporary_directory() as dest, ExitStack() as stack:
            flac = _write(stack, src, ".flac", b"audio")
            jpg = _write(stack, src, ".jpg", b"image")
            txt = _write(stack, src, ".txt", b"text")
            results = list(
                itreemap(
                    convert,
                    src,
                    dest,
                    extmap="flac",
                    filename_remap=lambda path: f"{path.stem}-out{path.suffix}",
                    copy_filtered_files=True,
                    copy_ext="jpg",
                    copy_filename_remap=lambda path: f"{path.stem}-copy{path.suffix}",
                    progress=False,
                )
            )

            self.assertEqual([(src_path, dest_path.read_bytes()) for src_path, dest_path, _ in results], [(flac, b"converted")])
            self.assertEqual(results[0][1].name, f"{flac.stem}-out.flac")
            self.assertEqual((dest / f"{jpg.stem}-copy.jpg").read_bytes(), b"image")
            self.assertFalse((dest / txt.name).exists())

    def test_max_depth(self):
        with temporary_directory() as src, temporary_directory() as dest, ExitStack() as stack:
            top = _write(stack, src, ".flac", b"top")
            nested_dir = src / "nested"
            nested_dir.mkdir()
            nested = _write(stack, nested_dir, ".flac", b"nested")
            deep_dir = nested_dir / "deep"
            deep_dir.mkdir()
            _write(stack, deep_dir, ".flac", b"deep")

            seen = {path.relative_to(src) for path, _, _ in itreemap(lambda src, dest: None, src, dest, extmap="flac", max_depth=1, progress=False)}

            self.assertEqual(seen, {top.relative_to(src), nested.relative_to(src)})
            self.assertFalse((dest / "nested" / "deep").exists())

    def test_dry_run(self):
        output = io.StringIO()
        with temporary_directory() as src, temporary_directory() as dest, ExitStack() as stack:
            src_file = _write(stack, src, ".flac", b"audio")
            called = False

            def func(src: Path, dest: Path) -> None:
                nonlocal called
                called = True

            results = list(itreemap(func, src, dest, extmap="flac", dry=True, progress=False, console=Console(file=output)))

            self.assertEqual(results, [])
            self.assertFalse(called)
            self.assertEqual(list(dest.iterdir()), [])
            self.assertIn(str(src_file), output.getvalue())
            self.assertIn(str(dest / src_file.name), output.getvalue())

    def test_rejects_nondirectory(self):
        with temporary_file() as (_, path), temporary_directory() as dest:
            with self.assertRaisesRegex(ValueError, "not a directory"):
                list(itreemap(lambda src, dest: None, path, dest, progress=False))
