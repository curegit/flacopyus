import io
from contextlib import redirect_stdout, redirect_stderr
from unittest import TestCase
from flacopyus import cli


class CLITest(TestCase):
    subcommands = ["sync", "test"]

    def test_no_args(self):
        with redirect_stderr(i := io.StringIO()):
            with self.assertRaises(SystemExit):
                cli.main(argv=[])
        self.assertTrue(i.getvalue())

    def test_help(self):
        with redirect_stdout(i := io.StringIO()):
            with self.assertRaises(SystemExit):
                cli.main(argv=["-h"])
        self.assertTrue(i.getvalue())

    def test_version(self):
        with redirect_stdout(i := io.StringIO()):
            with self.assertRaises(SystemExit):
                cli.main(argv=["-v"])
        self.assertTrue(i.getvalue())

    def test_subcommand_help(self):
        for subcommand in self.subcommands:
            with self.subTest(subcommand=subcommand):
                with redirect_stdout(i := io.StringIO()):
                    with self.assertRaises(SystemExit):
                        cli.main(argv=[subcommand, "-h"])
                self.assertTrue(i.getvalue())
