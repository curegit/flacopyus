from unittest import TestCase
from flacopyus.test import main


class TestMainTest(TestCase):
    def test_main(self):
        for v in [True, False]:
            with self.subTest(verbose=v):
                main(verbose=v)
