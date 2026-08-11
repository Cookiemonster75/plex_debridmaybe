import types
import unittest

from torrentio_parser import parse_stream

# Real Torrentio stream title captured from
# https://torrentio.strem.fun/.../stream/movie/tt0111161.json
REAL_TITLE = (
    "Побег из Шоушенка / The Shawshank Redemption [1994 UHD BDRemux 2160p HDR10 "
    "Dolby Vision] [Hybrid] 2x Dub + 6x MVO + 4x DVO + 9x AVO + Original (Eng) "
    "+ Sub (Rus Eng)\n👤 4 💾 78.61 GB ⚙️ Rutracker\n🇬🇧 / 🇷🇺"
)
FAKE_HASH = "0123456789abcdef0123456789abcdef01234567"


class TestParseStream(unittest.TestCase):
    def test_real_torrentio_title_dict_input(self):
        parsed = parse_stream({"title": REAL_TITLE, "infoHash": FAKE_HASH})
        self.assertIsNotNone(parsed)
        self.assertEqual(
            parsed["title"],
            "Побег.из.Шоушенка./.The.Shawshank.Redemption.[1994.UHD.BDRemux.2160p.HDR10."
            "Dolby.Vision].[Hybrid].2x.Dub.+.6x.MVO.+.4x.DVO.+.9x.AVO.+.Original.(Eng)."
            "+.Sub.(Rus.Eng)",
        )
        self.assertEqual(parsed["size"], 78.61)
        self.assertEqual(parsed["seeds"], 4)
        self.assertEqual(parsed["source"], "Rutracker")
        self.assertEqual(
            parsed["link"],
            "magnet:?xt=urn:btih:" + FAKE_HASH + "&dn=&tr=",
        )

    def test_attribute_object_input(self):
        stream = types.SimpleNamespace(
            title="Some Movie [2023] [1080p] [BluRay]\n👤 120 💾 2.5 GB ⚙️ rarbg",
            infoHash=FAKE_HASH,
        )
        parsed = parse_stream(stream)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["title"], "Some.Movie.[2023].[1080p].[BluRay]")
        self.assertEqual(parsed["size"], 2.5)
        self.assertEqual(parsed["seeds"], 120)
        self.assertEqual(parsed["source"], "rarbg")

    def test_missing_infohash_returns_none(self):
        self.assertIsNone(parse_stream({"title": "Some Movie\n👤 1 💾 1 GB ⚙️ tpb"}))
        self.assertIsNone(parse_stream(types.SimpleNamespace(title="Some Movie")))

    def test_missing_title_returns_none(self):
        self.assertIsNone(parse_stream({"infoHash": FAKE_HASH}))

    def test_mb_size_is_converted_to_gb(self):
        parsed = parse_stream({"title": "Some Movie\n👤 3 💾 800 MB ⚙️ tpb", "infoHash": FAKE_HASH})
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["size"], 0.8)

    def test_no_emoji_metadata_uses_defaults(self):
        parsed = parse_stream({"title": "Some Movie [1080p]", "infoHash": FAKE_HASH})
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["size"], 0)
        self.assertEqual(parsed["seeds"], 0)
        self.assertEqual(parsed["source"], "unknown")
        self.assertEqual(parsed["title"], "Some.Movie.[1080p]")

    def test_zero_seeders(self):
        parsed = parse_stream({"title": "Some Movie\n👤 0 💾 1.5 GB ⚙️ tpb", "infoHash": FAKE_HASH})
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["seeds"], 0)

    def test_double_digit_seeders(self):
        parsed = parse_stream({"title": "Some Movie\n👤 10 💾 1.5 GB ⚙️ tpb", "infoHash": FAKE_HASH})
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["seeds"], 10)

    def test_source_truncated_at_newline(self):
        parsed = parse_stream({"title": "Some Movie\n👤 1 💾 1 GB ⚙️ PrivateTracker\nExtra", "infoHash": FAKE_HASH})
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["source"], "PrivateTracker")

    def test_bad_metadata_returns_none_instead_of_raising(self):
        # "12x5" would match the loose size pattern but is not a valid float;
        # the entry must be skipped, not crash the whole scrape.
        self.assertIsNone(
            parse_stream({"title": "Some Movie\n👤 1 💾 12x5 GB ⚙️ tpb", "infoHash": FAKE_HASH})
        )


if __name__ == "__main__":
    unittest.main()
