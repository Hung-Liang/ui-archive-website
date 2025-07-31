import json
import os
import re
from datetime import datetime

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


def fetch_videos_from_playlist(playlist_id, max_results=30):
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

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    for item in data.get("items", []):
        snippet = item["snippet"]
        video_id = item["contentDetails"]["videoId"]

        if not snippet["title"] or not video_id:
            continue

        # Parse tags
        tags = parse_description_for_tags(snippet.get("description", ""))

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
        }
        videos.append(video)

    return videos


def fetch_all_videos_from_playlist(playlist_id):
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

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        for item in data.get("items", []):
            snippet = item["snippet"]
            video_id = item["contentDetails"]["videoId"]

            # Exclude entries with empty title or video ID
            if not snippet["title"] or not video_id:
                continue

            # Parse tags
            tags = parse_description_for_tags(snippet.get("description", ""))

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
            }
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

    dir_path = f"data/{category}/{sub_category}/{year}"
    os.makedirs(dir_path, exist_ok=True)

    path = get_save_path(category, sub_category, year, month)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted_videos, f, ensure_ascii=False, indent=2)


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

    with open(
        os.path.join(base_data_path, "index.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


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
                            all_videos_data.append(
                                {
                                    "title": video["title"],
                                    "videoId": video["videoId"],
                                    "publishedAt": video["publishedAt"],
                                    "channelTitle": video["channelTitle"],
                                    "thumbnail": video["thumbnail"],
                                    "category": category_folder,
                                    "subCategory": sub_category_folder,
                                    "year": int(year_folder),
                                    "month": month,
                                    "tags": video.get(
                                        "tags", []
                                    ),  # Include tags field
                                }
                            )
    all_videos_data.sort(
        key=lambda x: datetime.fromisoformat(
            x["publishedAt"].replace("Z", "+00:00")
        ),
        reverse=True,
    )

    index_path = os.path.join(base_data_path, "all_videos_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(all_videos_data, f, ensure_ascii=False, indent=2)
    print(
        f"Generated {len(all_videos_data)} entries in all_videos_index.json."
    )


def update_last_update_date():
    """Updates the last update date to the file."""
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(LAST_UPDATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_update": today}, f, ensure_ascii=False, indent=2)
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

            videos = fetch_videos_from_playlist(playlist_id, max_results=30)
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

    for category, sub_categories in PLAYLIST_IDS.items():
        for sub_category, playlist_id in sub_categories.items():
            print(
                f"Fetching all historical videos from '{category}' "
                f"-> '{sub_category}' (Playlist: {playlist_id})..."
            )

            videos = fetch_all_videos_from_playlist(playlist_id)
            print(
                f"Fetched {len(videos)} videos from '{category}' "
                f"-> '{sub_category}'."
            )

            process_videos_for_saving(videos, category, sub_category)

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
