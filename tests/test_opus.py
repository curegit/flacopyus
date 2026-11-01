from unittest import TestCase
from flacopyus.opus import BitrateMode, Downmix, LowBitrateTuning, OpusOptions


class OpusOptionsTest(TestCase):
    def test_to_cmd_line_args(self):
        cases = (
            (OpusOptions(), ["--bitrate", "128", "--vbr"]),
            (
                OpusOptions(bitrate=96, bitrate_mode=BitrateMode.HardCBR, low_bitrate_tuning=LowBitrateTuning.Speech, downmix=Downmix.Mono),
                ["--bitrate", "96", "--hard-cbr", "--speech", "--downmix-mono"],
            ),
            (
                OpusOptions(bitrate_mode=BitrateMode.CBR, low_bitrate_tuning=LowBitrateTuning.Music, downmix=Downmix.Stereo),
                ["--bitrate", "128", "--cbr", "--music", "--downmix-stereo"],
            ),
        )
        for options, expected in cases:
            with self.subTest(options=options):
                self.assertEqual(options.to_cmd_line_args(), expected)
