import json
import os
import re
import tempfile
from datetime import datetime, timezone

import requests

API_KEY = os.environ.get("YOUTUBE_API_KEY")

# File to store the last update date
LAST_UPDATE_FILE = "data/last_update.json"


PLAYLIST_IDS = {
    "videos": {
        "normal": "UUt30jJgChL8qeT9VPadidSw",
        "member": "UUMOt30jJgChL8qeT9VPadidSw",
    }
}


def parse_description_for_tags(description):
    """
    Parses video description to extract tags.
    Currently empty, awaiting your algorithm.
    """

    tags = []

    all_tags = re.findall(r"#(\w+)", description)
    for tag in all_tags:
        tags.append(tag)

    return tags


def parse_duration(duration):
    """Parses ISO 8601 duration to a formatted string (H:MM:SS, MM:SS, etc.)."""
    if not duration:
        return ""

    match = re.match(
        r'P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration
    )
    if not match:
        return ""

    days, hours, minutes, seconds = match.groups()
    days = int(days) if days else 0
    hours = int(hours) if hours else 0
    minutes = int(minutes) if minutes else 0
    seconds = int(seconds) if seconds else 0

    total_hours = days * 24 + hours

    if total_hours > 0:
        return f"{total_hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"


def fetch_video_details(video_ids, include_view_count=True):
    """Fetches duration and view count for a list of video IDs (max 50)."""
    if not video_ids:
        return {}

    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "key": API_KEY,
        "id": ",".join(video_ids),
        "part": (
            "contentDetails,statistics"
            if include_view_count
            else "contentDetails"
        ),
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    details = {}
    for item in data.get("items", []):
        video_id = item["id"]
        duration = item["contentDetails"].get("duration")

        details[video_id] = {"duration": parse_duration(duration)}
        if include_view_count:
            details[video_id]["viewCount"] = item["statistics"].get(
                "viewCount", "0"
            )

    return details


def fetch_videos_from_playlist(
    playlist_id, max_results=30, include_view_count=True
):
    """
    Fetches the latest videos from the specified playlist,
    defaulting to max 30 results.
    This function is used for daily updates.
    """
    videos = []
    url = "https://www.googleapis.com/youtube/v3/playlistItems"

    params = {
        "key": API_KEY,
        "playlistId": playlist_id,
        "part": "snippet,contentDetails",
        "maxResults": max_results,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    video_ids = [
        item["contentDetails"]["videoId"] for item in data.get("items", [])
    ]
    details = fetch_video_details(video_ids, include_view_count)

    for item in data.get("items", []):
        snippet = item["snippet"]
        video_id = item["contentDetails"]["videoId"]

        if not snippet["title"] or not video_id:
            continue

        # Parse tags
        tags = parse_description_for_tags(snippet.get("description", ""))

        video_info = details.get(video_id, {"duration": ""})

        video = {
            "title": snippet["title"],
            "videoId": video_id,
            "description": snippet["description"],
            "channelTitle": snippet["channelTitle"],
            "publishedAt": snippet["publishedAt"],
            "thumbnail": (
                snippet["thumbnails"]["high"]["url"]
                if "high" in snippet["thumbnails"]
                else ""
            ),
            "playlistId": playlist_id,
            "tags": tags,  # Add tags field
            "duration": video_info["duration"],
        }
        if include_view_count:
            video["viewCount"] = video_info.get("viewCount", "0")
        videos.append(video)

    return videos


def fetch_all_videos_from_playlist(playlist_id, include_view_count=True):
    """
    Fetches all videos from the specified playlist.
    This function is for initialization and will paginate through all results.
    """
    videos = []
    next_page_token = None
    url = "https://www.googleapis.com/youtube/v3/playlistItems"

    while True:
        params = {
            "key": API_KEY,
            "playlistId": playlist_id,
            "part": "snippet,contentDetails",
            "maxResults": 50,
            "pageToken": next_page_token,
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        video_ids = [
            item["contentDetails"]["videoId"] for item in data.get("items", [])
        ]
        details = fetch_video_details(video_ids, include_view_count)

        for item in data.get("items", []):
            snippet = item["snippet"]
            video_id = item["contentDetails"]["videoId"]

            # Exclude entries with empty title or video ID
            if not snippet["title"] or not video_id:
                continue

            # Parse tags
            tags = parse_description_for_tags(snippet.get("description", ""))

            video_info = details.get(video_id, {"duration": ""})

            video = {
                "title": snippet["title"],
                "videoId": video_id,
                "description": snippet["description"],
                "channelTitle": snippet["channelTitle"],
                "publishedAt": snippet["publishedAt"],
                "thumbnail": (
                    snippet["thumbnails"]["high"]["url"]
                    if "high" in snippet["thumbnails"]
                    else ""
                ),
                "playlistId": playlist_id,
                "tags": tags,  # Add tags field
                "duration": video_info["duration"],
            }
            if include_view_count:
                video["viewCount"] = video_info.get("viewCount", "0")
            videos.append(video)

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break
    return videos


def get_save_path(category, sub_category, year, month):
    """Constructs the save path based on
    category, sub_category, year, and month.
    """
    return f"data/{category}/{sub_category}/{year}/{month:02d}.json"


def atomic_save_json(data, filepath, compact=False):
    """
    Saves JSON data atomically to prevent file corruption during
    unexpected termination.
    """
    dir_path = os.path.dirname(filepath)
    os.makedirs(dir_path, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            if compact:
                json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
            else:
                json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, filepath)
    except BaseException:
        os.remove(temp_path)
        raise


def load_existing_videos(category, sub_category, year, month):
    """
    Loads existing video data based on the new path structure.
    """
    path = get_save_path(category, sub_category, year, month)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json_merged(new_videos, category, sub_category, year, month):
    """
    Merges new and existing video data,
    sorts by publish time in descending order, and saves
    to the new path structure.
    """
    if not new_videos:
        return

    existing_videos = load_existing_videos(category, sub_category, year, month)

    combined_dict = {v["videoId"]: v for v in existing_videos}
    for video in new_videos:
        combined_dict[video["videoId"]] = video

    sorted_videos = sorted(
        list(combined_dict.values()),
        key=lambda x: datetime.fromisoformat(
            x["publishedAt"].replace("Z", "+00:00")
        ),
        reverse=True,
    )

    path = get_save_path(category, sub_category, year, month)
    atomic_save_json(sorted_videos, path)


def update_index_json():
    """
    Updates data/index.json, recording which years and months have data
    under each category/sub_category.
    The index file structure will reflect the new directory hierarchy.
    """
    index = {}

    base_data_path = "data"
    if not os.path.exists(base_data_path):
        return

    category_folders = sorted(os.listdir(base_data_path))
    for category_folder in category_folders:
        category_path = os.path.join(base_data_path, category_folder)
        if (
            not os.path.isdir(category_path)
            or category_folder.startswith('.')
            or category_folder == 'index.json'
            or category_folder
            == 'all_videos_index.json'  # Exclude new index file
            or category_folder
            == 'last_update.json'  # Exclude last update file
        ):
            continue

        index[category_folder] = {}

        sub_category_folders = sorted(os.listdir(category_path))
        for sub_category_folder in sub_category_folders:
            sub_category_path = os.path.join(
                category_path, sub_category_folder
            )
            if not os.path.isdir(
                sub_category_path
            ) or sub_category_folder.startswith('.'):
                continue

            index[category_folder][sub_category_folder] = {}

            year_folders = sorted(
                [f for f in os.listdir(sub_category_path) if f.isdigit()],
                key=int,
            )
            for year_folder in year_folders:
                year_path = os.path.join(sub_category_path, year_folder)
                if not os.path.isdir(year_path):
                    continue

                months = []
                for file in os.listdir(year_path):
                    if file.endswith(".json") and file[:-5].isdigit():
                        months.append(int(file[:-5]))

                if months:
                    index[category_folder][sub_category_folder][
                        int(year_folder)
                    ] = sorted(months, reverse=True)

    atomic_save_json(index, os.path.join(base_data_path, "index.json"))


def process_videos_for_saving(videos, category, sub_category):
    """
    A generic function to group videos by month and save them.
    """
    if not videos:
        print(f"No videos to process for '{category}' -> '{sub_category}'.")
        return

    videos_by_month = {}
    for video in videos:
        published_at_dt = datetime.fromisoformat(
            video["publishedAt"].replace("Z", "+00:00")
        )
        year_month_key = (published_at_dt.year, published_at_dt.month)

        if year_month_key not in videos_by_month:
            videos_by_month[year_month_key] = []
        videos_by_month[year_month_key].append(video)

    for (year, month), videos_to_save in videos_by_month.items():
        print(
            f"Saving {len(videos_to_save)} videos for '{category}' "
            f"-> '{sub_category}' {year}-{month:02d}..."
        )
        save_json_merged(videos_to_save, category, sub_category, year, month)
        print(
            f"Videos saved for '{category}' "
            f"-> '{sub_category}' {year}-{month:02d}."
        )


def generate_all_videos_index():
    """
    Generates a single JSON file (data/all_videos_index.json)
    containing metadata for
    all videos across all categories/sub-categories/years/months.
    This file will be used for client-side search.
    """
    print("--- Generating All Videos Index ---")
    all_videos_data = []
    base_data_path = "data"

    if not os.path.exists(base_data_path):
        print("Data directory not found. Skipping index generation.")
        return

    for category_folder in os.listdir(base_data_path):
        category_path = os.path.join(base_data_path, category_folder)
        if (
            not os.path.isdir(category_path)
            or category_folder.startswith('.')
            or category_folder == 'index.json'
            or category_folder == 'all_videos_index.json'
            or category_folder
            == 'last_update.json'  # Exclude last update file
        ):
            continue

        for sub_category_folder in os.listdir(category_path):
            sub_category_path = os.path.join(
                category_path, sub_category_folder
            )
            if not os.path.isdir(
                sub_category_path
            ) or sub_category_folder.startswith('.'):
                continue

            for year_folder in os.listdir(sub_category_path):
                if not year_folder.isdigit():
                    continue
                year_path = os.path.join(sub_category_path, year_folder)
                if not os.path.isdir(year_path):
                    continue

                for file in os.listdir(year_path):
                    if file.endswith(".json") and file[:-5].isdigit():
                        month = int(file[:-5])
                        videos_in_month = load_existing_videos(
                            category_folder,
                            sub_category_folder,
                            int(year_folder),
                            month,
                        )
                        for video in videos_in_month:
                            entry = {
                                "title": video["title"],
                                "videoId": video["videoId"],
                                "publishedAt": video["publishedAt"],
                                "category": category_folder,
                                "subCategory": sub_category_folder,
                                "year": int(year_folder),
                                "month": month,
                                "duration": video.get("duration", ""),
                            }
                            if "viewCount" in video:
                                entry["viewCount"] = video["viewCount"]
                            # Omit fields the frontend can derive to keep
                            # the search index small
                            thumbnail = video.get("thumbnail", "")
                            if thumbnail and thumbnail != (
                                "https://i.ytimg.com/vi/"
                                f"{video['videoId']}/hqdefault.jpg"
                            ):
                                entry["thumbnail"] = thumbnail
                            if video.get("tags"):
                                entry["tags"] = video["tags"]
                            all_videos_data.append(entry)
    all_videos_data.sort(
        key=lambda x: datetime.fromisoformat(
            x["publishedAt"].replace("Z", "+00:00")
        ),
        reverse=True,
    )

    index_path = os.path.join(base_data_path, "all_videos_index.json")
    atomic_save_json(all_videos_data, index_path, compact=True)
    print(
        f"Generated {len(all_videos_data)} entries in all_videos_index.json."
    )


def update_last_update_date():
    """Updates the last update date to the file."""
    today = datetime.now(timezone.utc).isoformat(timespec="minutes")
    atomic_save_json({"last_update": today}, LAST_UPDATE_FILE)
    print(f"Last update date updated to: {today}")


def daily_update():
    """Executes the daily update, fetching only the latest 30 videos."""
    print("--- Executing Daily Update (Fetching Latest 30 Videos) ---")
    for category, sub_categories in PLAYLIST_IDS.items():
        for sub_category, playlist_id in sub_categories.items():
            print(
                f"Fetching latest 30 videos from '{category}' "
                f"-> '{sub_category}' (Playlist: {playlist_id})..."
            )

            videos = fetch_videos_from_playlist(
                playlist_id,
                max_results=30,
                include_view_count=sub_category != "member",
            )
            print(
                f"Fetched {len(videos)} videos from '{category}' "
                f"-> '{sub_category}'."
            )

            process_videos_for_saving(videos, category, sub_category)

    update_index_json()
    generate_all_videos_index()
    update_last_update_date()
    print("Index file updated.")
    print("Daily update complete.")


def clean_up_local_data(all_fetched_video_metadata):
    """
    Scans all local JSON files in data/ and removes videos that are no longer
    present in the fetched metadata or have moved to a different category.
    """
    print("--- Starting Local Data Clean-up ---")
    base_data_path = "data"
    if not os.path.exists(base_data_path):
        return

    removed_count = 0
    for category_folder in os.listdir(base_data_path):
        category_path = os.path.join(base_data_path, category_folder)
        if (
            not os.path.isdir(category_path)
            or category_folder.startswith('.')
            or category_folder in ['index.json', 'all_videos_index.json', 'last_update.json']
        ):
            continue

        for sub_category_folder in os.listdir(category_path):
            sub_category_path = os.path.join(category_path, sub_category_folder)
            if not os.path.isdir(sub_category_path) or sub_category_folder.startswith('.'):
                continue

            for year_folder in os.listdir(sub_category_path):
                if not year_folder.isdigit():
                    continue
                year_path = os.path.join(sub_category_path, year_folder)
                
                for file in os.listdir(year_path):
                    if file.endswith(".json") and file[:-5].isdigit():
                        month = int(file[:-5])
                        path = get_save_path(category_folder, sub_category_folder, int(year_folder), month)
                        
                        with open(path, "r", encoding="utf-8") as f:
                            videos = json.load(f)
                        
                        original_count = len(videos)
                        # Filter videos: must be in metadata AND in the correct category/sub_category
                        pruned_videos = []
                        for v in videos:
                            video_id = v["videoId"]
                            if video_id in all_fetched_video_metadata:
                                expected_cat, expected_sub_cat = all_fetched_video_metadata[video_id]
                                if expected_cat == category_folder and expected_sub_cat == sub_category_folder:
                                    pruned_videos.append(v)
                                else:
                                    print(f"Video {video_id} moved: {category_folder}/{sub_category_folder} -> {expected_cat}/{expected_sub_cat}")
                            else:
                                print(f"Video {video_id} not found in playlists, removing from {path}")
                        
                        if len(pruned_videos) != original_count:
                            removed_count += (original_count - len(pruned_videos))
                            atomic_save_json(pruned_videos, path)
    
    print(f"Clean-up complete. Removed {removed_count} orphaned or misplaced video entries.")


def initialize_all_playlists():
    """
    Executes initialization, fetching all videos from all playlists.
    WARNING: This operation will consume a significant amount of API quota.
    """
    print("--- Executing Initialization (Fetching All Historical Videos) ---")
    print(
        "WARNING: This operation will consume a significant amount of "
        "API quota. Use with caution."
    )

    all_fetched_video_metadata = {}
    fetched_playlists = []

    # Fetch every playlist before writing anything, so a failed or
    # empty fetch can never trigger clean-up on incomplete metadata.
    for category, sub_categories in PLAYLIST_IDS.items():
        for sub_category, playlist_id in sub_categories.items():
            print(
                f"Fetching all historical videos from '{category}' "
                f"-> '{sub_category}' (Playlist: {playlist_id})..."
            )

            videos = fetch_all_videos_from_playlist(
                playlist_id, include_view_count=sub_category != "member"
            )
            print(
                f"Fetched {len(videos)} videos from '{category}' "
                f"-> '{sub_category}'."
            )

            if not videos:
                raise RuntimeError(
                    f"Playlist {playlist_id} ('{category}' -> "
                    f"'{sub_category}') returned no videos. "
                    "Aborting to prevent data loss."
                )

            # Populate metadata for clean-up
            for v in videos:
                all_fetched_video_metadata[v["videoId"]] = (category, sub_category)

            fetched_playlists.append((videos, category, sub_category))

    for videos, category, sub_category in fetched_playlists:
        process_videos_for_saving(videos, category, sub_category)

    clean_up_local_data(all_fetched_video_metadata)
    update_index_json()
    generate_all_videos_index()
    update_last_update_date()
    print("Index file updated.")
    print("Initialization complete.")


def main():
    """
    Main execution function. Can choose to perform daily update
    or initialization
    via command-line arguments.
    Examples:
    python your_script_name.py daily_update
    python your_script_name.py initialize
    If no argument is provided, 'daily_update' will be executed by default.
    """
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "initialize":
            initialize_all_playlists()
        elif command == "daily_update":
            daily_update()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: initialize, daily_update")
            print("Defaulting to daily_update.")
            daily_update()
    else:
        daily_update()

    print("All operations finished.")


if __name__ == "__main__":
    main()
