import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import update  # noqa: E402

EXPECTED_LOCATION = ("videos", "normal")


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

    def test_deduplicates_tags(self):
        self.assertEqual(update.parse_description_for_tags("#a #a"), ["a"])

    def test_ignores_url_fragments(self):
        self.assertEqual(
            update.parse_description_for_tags("https://a.com/p#x #real"),
            ["real"],
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


class KeepStoredFieldsTest(DataDirTestCase):
    def api_video(self, video_id, published_at, **fields):
        video = make_video(video_id, published_at, **fields)
        for field in ("thumbnail", "duration", "viewCount"):
            if field not in fields:
                del video[field]
        return video

    def test_fetch_details_omits_what_the_api_did_not_return(self):
        response = mock.Mock()
        response.json.return_value = {
            "items": [
                {"id": "a", "contentDetails": {"duration": "P0D"}, "statistics": {}},
                {"id": "b", "contentDetails": {"duration": "PT10M"},
                 "statistics": {"viewCount": "7"}},
            ]
        }
        with mock.patch.object(update.requests, "get", return_value=response):
            details = update.fetch_video_details(["a", "b"])
        self.assertEqual(
            details, {"a": {}, "b": {"duration": "10:00", "viewCount": "7"}}
        )

    def test_build_video_omits_missing_details(self):
        item = {
            "snippet": {
                "title": "t",
                "description": "",
                "channelTitle": "c",
                "publishedAt": "2026-01-05T00:00:00Z",
                "thumbnails": {},
            },
            "contentDetails": {"videoId": "a"},
        }
        video = update.build_video(item, {}, "playlist", True)
        for field in ("thumbnail", "duration", "viewCount"):
            self.assertNotIn(field, video)

    def test_missing_fields_keep_stored_values(self):
        stored = make_video("a", "2026-01-05T00:00:00Z", title="old")
        path = self.write_month([stored], category="c")
        new = self.api_video("a", "2026-01-05T00:00:00Z", title="new")
        update.save_json_merged([new], "c", "normal", 2026, 1)
        self.assertEqual(self.read_json(path), [dict(stored, title="new")])

    def test_returned_fields_are_updated(self):
        path = self.write_month([make_video("a", "2026-01-05T00:00:00Z")], category="c")
        fresh = make_video(
            "a", "2026-01-05T00:00:00Z", duration="2:00", viewCount="99", thumbnail="new"
        )
        update.save_json_merged([fresh], "c", "normal", 2026, 1)
        self.assertEqual(self.read_json(path), [fresh])

    def test_new_video_without_details_gets_empty_values(self):
        new = self.api_video("a", "2026-01-05T00:00:00Z")
        update.save_json_merged([new], "c", "normal", 2026, 1)
        saved = self.read_json(update.get_save_path("c", "normal", 2026, 1))[0]
        self.assertEqual(
            (saved["thumbnail"], saved["duration"], saved["viewCount"]), ("", "", "0")
        )

    def test_member_video_does_not_keep_view_count(self):
        stored = make_video("a", "2026-01-05T00:00:00Z")
        path = self.write_month([stored], category="c", sub="member")
        new = self.api_video("a", "2026-01-05T00:00:00Z")
        update.save_json_merged([new], "c", "member", 2026, 1)
        saved = self.read_json(path)[0]
        self.assertNotIn("viewCount", saved)
        self.assertEqual(saved["duration"], stored["duration"])

    def test_video_moved_to_member_does_not_keep_view_count(self):
        self.write_month([make_video("a", "2026-01-05T00:00:00Z")], category="c")
        new = self.api_video("a", "2026-01-05T00:00:00Z")
        update.process_videos_for_saving([new], "c", "member")
        path = update.get_save_path("c", "member", 2026, 1)
        self.assertNotIn("viewCount", self.read_json(path)[0])

    def test_month_change_keeps_values_from_the_newest_copy(self):
        stale = make_video("a", "2026-01-20T00:00:00Z", duration="", viewCount="0")
        good = make_video("a", "2026-02-03T00:00:00Z", duration="3:00", viewCount="531")
        self.write_month([stale], category="c", month=1)
        self.write_month([good], category="c", month=2)
        new = self.api_video("a", "2026-03-10T00:00:00Z")

        update.process_videos_for_saving([new], "c", "normal")

        saved = self.read_json(update.get_save_path("c", "normal", 2026, 3))[0]
        self.assertEqual((saved["duration"], saved["viewCount"]), ("3:00", "531"))


    def test_newest_copy_wins_over_stale_copy_in_another_sub_category(self):
        stale = make_video("a", "2026-01-03T00:00:00Z", thumbnail="stale")
        good = make_video("a", "2026-01-05T00:00:00Z", thumbnail="good")
        self.write_month([stale], category="c", sub="normal")
        path = self.write_month([good], category="c", sub="member")
        new = self.api_video("a", "2026-01-05T00:00:00Z")

        update.process_videos_for_saving([new], "c", "member")

        self.assertEqual(self.read_json(path)[0]["thumbnail"], "good")


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


class CleanUpLocalDataTest(DataDirTestCase):
    def test_removes_only_videos_missing_from_playlists(self):
        keep = make_video("keep", "2026-01-05T00:00:00Z")
        gone = make_video("gone", "2026-01-06T00:00:00Z")
        path = self.write_month([gone, keep], category="videos")
        update.clean_up_local_data({"keep": EXPECTED_LOCATION + (2026, 1)})
        self.assertEqual(self.read_json(path), [keep])

    def test_removes_videos_moved_to_another_location(self):
        moved = make_video("moved", "2026-01-05T00:00:00Z")
        category, sub_category = EXPECTED_LOCATION
        for location in [
            ("other", sub_category, 2026, 1),
            (category, "member", 2026, 1),
            (category, sub_category, 2026, 2),
            (category, sub_category, 2025, 1),
        ]:
            with self.subTest(location=location):
                path = self.write_month([moved], category=category)
                update.clean_up_local_data({"moved": location})
                self.assertFalse(os.path.exists(path))

    def test_keeps_missing_videos_when_remove_missing_is_false(self):
        category, sub_category = EXPECTED_LOCATION
        old = make_video("old", "2026-01-05T00:00:00Z")
        stale = make_video("stale", "2026-01-06T00:00:00Z", duration="")
        path = self.write_month([stale, old], category=category)
        update.clean_up_local_data(
            {"stale": (category, sub_category, 2026, 2)}, remove_missing=False
        )
        self.assertEqual(self.read_json(path), [old])

    def test_emptied_month_is_deleted_and_leaves_the_index(self):
        category, sub_category = EXPECTED_LOCATION
        keep = make_video("keep", "2026-02-05T00:00:00Z")
        gone = make_video("gone", "2026-01-05T00:00:00Z")
        emptied = self.write_month([gone], category=category, month=1)
        self.write_month([keep], category=category, month=2)

        update.clean_up_local_data({"keep": EXPECTED_LOCATION + (2026, 2)})
        update.update_index_json()

        self.assertFalse(os.path.exists(emptied))
        self.assertEqual(
            self.read_json("data/index.json"),
            {category: {sub_category: {"2026": [2]}}},
        )


class DailyUpdateTest(DataDirTestCase):
    def run_daily_update(self, latest):
        category, sub_category = EXPECTED_LOCATION
        playlist_id = update.PLAYLIST_IDS[category][sub_category]
        with mock.patch.object(
            update,
            "fetch_videos_from_playlist",
            side_effect=lambda pid, **_: latest if pid == playlist_id else [],
        ):
            update.daily_update()

    def test_publish_month_change_leaves_one_copy(self):
        category, sub_category = EXPECTED_LOCATION
        stale = make_video("live", "2026-01-20T00:00:00Z", duration="")
        old = make_video("old", "2026-01-05T00:00:00Z")
        january = self.write_month([stale, old], category=category, month=1)
        fresh = make_video("live", "2026-02-03T00:00:00Z")

        self.run_daily_update([fresh])

        self.assertEqual(self.read_json(january), [old])
        index = self.read_json("data/all_videos_index.json")
        self.assertEqual(
            sorted((v["videoId"], v["month"]) for v in index),
            [("live", 2), ("old", 1)],
        )

    def test_keeps_videos_outside_the_latest_batch(self):
        category, _ = EXPECTED_LOCATION
        old = make_video("old", "2020-01-05T00:00:00Z")
        path = self.write_month([old], category=category, year=2020)

        self.run_daily_update([make_video("new", "2026-02-03T00:00:00Z")])

        self.assertEqual(self.read_json(path), [old])

    def test_empty_fetch_removes_nothing(self):
        category, _ = EXPECTED_LOCATION
        old = make_video("old", "2026-01-05T00:00:00Z")
        path = self.write_month([old], category=category)

        self.run_daily_update([])

        self.assertEqual(self.read_json(path), [old])


class InitializeGuardTest(DataDirTestCase):
    def test_full_sync_removes_missing_and_stale_copies(self):
        category, sub_category = EXPECTED_LOCATION
        stale = make_video("live", "2026-01-20T00:00:00Z", duration="")
        gone = make_video("gone", "2026-01-05T00:00:00Z")
        january = self.write_month([stale, gone], category=category, month=1)
        fresh = make_video("live", "2026-02-03T00:00:00Z")
        playlist_id = update.PLAYLIST_IDS[category][sub_category]
        other = make_video("other", "2026-02-04T00:00:00Z")

        with mock.patch.object(
            update,
            "fetch_all_videos_from_playlist",
            side_effect=lambda pid, **_: [fresh] if pid == playlist_id else [other],
        ):
            update.initialize_all_playlists()

        self.assertFalse(os.path.exists(january))
        index = self.read_json("data/all_videos_index.json")
        self.assertEqual(
            sorted(v["videoId"] for v in index), ["live", "other"]
        )

    def test_empty_playlist_aborts_before_writing(self):
        video = make_video("a", "2026-01-05T00:00:00Z")
        with mock.patch.object(
            update, "fetch_all_videos_from_playlist", side_effect=[[video], []]
        ):
            with self.assertRaises(RuntimeError):
                update.initialize_all_playlists()
        self.assertFalse(os.path.exists("data"))


if __name__ == "__main__":
    unittest.main()
