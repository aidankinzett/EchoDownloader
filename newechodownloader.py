"""
Download videos from Echo360 recordings.

Functions to:
    - Import config from YAML
    - Check RSS feeds
    - Check database
    - Download in LQ
    - Move and rename files (including HQ from flash downloader)

Todo:
    * Above stuff
    * Change check_database to check for wether or not the video has been downloaded,
      and does sqlite support bools?
    * Add error handling
    * More comments
"""
import os
import re
import sqlite3
import yaml
import feedparser

# opens the configuration file and save config as constants
with open("config.yml", 'r') as ymlfile:
    CONFIG = yaml.load(ymlfile)
RSS_FEEDS = CONFIG['rss feeds']
DOWNLOAD_DIRECTORY = CONFIG['file directory']
DB_PATH = DOWNLOAD_DIRECTORY + '/echodownloader.db'
HIGH_QUALITY = CONFIG['high quality']


def get_video_info(rss_feed):
    """Return info for all videos found in the given RSS feed.

    Args:
        rss_feed (str): The rss feed to check for videos

    Returns:
        list: List of found videos in format [[url,subject code, video title],...]

    """
    videos = []

    parsed_feed = feedparser.parse(rss_feed)
    for entry in parsed_feed.entries:
        codefind = re.findall(r'Course ID:.*?<br', str(entry))
        code = codefind[0][11:-3]

        title = entry.title

        enclose = entry.enclosures
        for dictionary in enclose:
            if 'type' in dictionary:
                if dictionary['type'] == 'video/mp4':
                    url = dictionary['href']

        videos.append([url, code, title])

    return videos

def check_database(videos):
    """Compare a list of given videos to list of videos in database.

    If database does not exist in the specified file directory, it is created.

    Args:
        videos (list): List of videos in format [[url,subject code, video title],...]

    Returns:
        list: List of videos not currently found in the database

    """
    new_videos = []

    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE "urls" ( `URL` TEXT, `Subject Code` TEXT,'+
                       '`Title` TEXT , `Downloaded` TEXT)')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for item in videos:
        dblist = []
        for row in cursor.execute("SELECT * FROM urls WHERE URL = ?", [item[0]]):
            dblist.append(row)

        if len(dblist) < 1:
            new_videos.append(item)

    conn.commit()
    conn.close()

    return new_videos

test_videos = get_video_info(RSS_FEEDS[0])
print(check_database(test_videos))
