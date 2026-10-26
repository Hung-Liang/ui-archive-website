import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import update  # noqa: E402


def make_video(video_id, published_at, **extra):
    video = {
        "title": f"title {video_id}",
        "videoId": video_id,
        "publishedAt": published_at,
        "channelTitle": "channel",
        "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "tags": [],
        "duration": "1:00:00",
        "viewCount": "10",
    }
    video.update(extra)
    return video


class ParseDurationTest(unittest.TestCase):
    def test_hours_minutes_seconds(self):
        self.assertEqual(update.parse_duration("PT1H2M3S"), "1:02:03")

    def test_minutes_only(self):
        self.assertEqual(update.parse_duration("PT10M"), "10:00")

    def test_seconds_only(self):
        self.assertEqual(update.parse_duration("PT45S"), "0:45")

    def test_days_roll_into_hours(self):
        self.assertEqual(update.parse_duration("P1DT2H3M4S"), "26:03:04")

    def test_empty_or_invalid(self):
        self.assertEqual(update.parse_duration(""), "")
        self.assertEqual(update.parse_duration(None), "")
        self.assertEqual(update.parse_duration("invalid"), "")
        # Upcoming/live streams report P0D without a time part
        self.assertEqual(update.parse_duration("P0D"), "")


class ParseDescriptionForTagsTest(unittest.TestCase):
    def test_extracts_hashtags_in_order(self):
        self.assertEqual(
            update.parse_description_for_tags("#ゲーム text #雑談"),
            ["ゲーム", "雑談"],
        )

    def test_keeps_duplicate_hashtags(self):
        self.assertEqual(
            update.parse_description_for_tags("#しぐれうい #しぐれうい"),
            ["しぐれうい", "しぐれうい"],
        )

    def test_no_tags(self):
        self.assertEqual(update.parse_description_for_tags("plain"), [])


class DataDirTestCase(unittest.TestCase):
    """Runs each test inside an empty temp dir, since update.py uses relative data/ paths."""

    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def write_month(self, videos, category="videos", sub="normal", year=2026, month=1):
        path = update.get_save_path(category, sub, year, month)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(videos, f, ensure_ascii=False)
        return path

    def read_json(self, path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)


class SaveJsonMergedTest(DataDirTestCase):
    def test_creates_file_when_missing(self):
        video = make_video("a", "2026-01-05T00:00:00Z")
        update.save_json_merged([video], "videos", "normal", 2026, 1)
        path = update.get_save_path("videos", "normal", 2026, 1)
        self.assertEqual(self.read_json(path), [video])

    def test_keeps_existing_videos_not_in_new_batch(self):
        old = make_video("old", "2026-01-01T00:00:00Z", title="手動修改")
        path = self.write_month([old])
        new = make_video("new", "2026-01-10T00:00:00Z")
        update.save_json_merged([new], "videos", "normal", 2026, 1)
        self.assertEqual(self.read_json(path), [new, old])

    def test_new_data_replaces_same_video_id(self):
        path = self.write_month([make_video("a", "2026-01-05T00:00:00Z", viewCount="1")])
        fresh = make_video("a", "2026-01-05T00:00:00Z", viewCount="99")
        update.save_json_merged([fresh], "videos", "normal", 2026, 1)
        self.assertEqual(self.read_json(path), [fresh])

    def test_sorted_newest_first(self):
        videos = [
            make_video("mid", "2026-01-15T00:00:00Z"),
            make_video("old", "2026-01-01T00:00:00Z"),
            make_video("new", "2026-01-31T23:59:59Z"),
        ]
        update.save_json_merged(videos, "videos", "normal", 2026, 1)
        path = update.get_save_path("videos", "normal", 2026, 1)
        self.assertEqual(
            [v["videoId"] for v in self.read_json(path)], ["new", "mid", "old"]
        )

    def test_empty_batch_leaves_file_untouched(self):
        path = self.write_month([make_video("a", "2026-01-05T00:00:00Z")])
        with open(path, "rb") as f:
            before = f.read()
        update.save_json_merged([], "videos", "normal", 2026, 1)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_no_temp_files_left_behind(self):
        update.save_json_merged(
            [make_video("a", "2026-01-05T00:00:00Z")], "videos", "normal", 2026, 1
        )
        folder = os.path.dirname(update.get_save_path("videos", "normal", 2026, 1))
        self.assertEqual(os.listdir(folder), ["01.json"])


class GenerateAllVideosIndexTest(DataDirTestCase):
    def test_compact_index_omits_derivable_fields(self):
        default_thumb = make_video("a", "2026-01-05T00:00:00Z", tags=["ゲーム"])
        custom_thumb = make_video(
            "b",
            "2026-01-06T00:00:00Z",
            thumbnail="https://i.ytimg.com/vi/b/hqdefault_live.jpg",
        )
        self.write_month([custom_thumb, default_thumb])

        update.generate_all_videos_index()

        with open("data/all_videos_index.json", encoding="utf-8") as f:
            raw = f.read()
        self.assertNotIn("\n", raw)
        index = json.loads(raw)
        self.assertEqual([v["videoId"] for v in index], ["b", "a"])
        b, a = index
        self.assertEqual(b["thumbnail"], "https://i.ytimg.com/vi/b/hqdefault_live.jpg")
        self.assertNotIn("tags", b)
        self.assertNotIn("thumbnail", a)
        self.assertEqual(a["tags"], ["ゲーム"])
        self.assertNotIn("channelTitle", a)
        self.assertEqual(
            (a["category"], a["subCategory"], a["year"], a["month"]),
            ("videos", "normal", 2026, 1),
        )


if __name__ == "__main__":
    unittest.main()
