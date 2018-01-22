"""Download videos from Echo360 recordings.

Functions to:
    - Import config from YAML
    - Check RSS feeds
    - Check database
    - Download in LQ
    - Move and rename files (including HQ from flash downloader)

Uses configuration from "config.yml"
"""
import os
import json
import re
import sqlite3
import sys
from urllib.request import URLopener
import yaml
import feedparser
import flashdownloader
from createDB import *
from createDB import Video
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.sqlite import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import *

# open the configuration file and save config as constants
with open("config.json", 'r') as ymlfile:
    CONFIG = json.load(ymlfile)

RSS_FEEDS = CONFIG['rss_feeds']
DOWNLOAD_DIRECTORY = 'static'
DB_PATH = os.path.join(DOWNLOAD_DIRECTORY, 'echodownloader.db')

def check_database_exists():
    """If the database doesnt exists in the specified folder, create one."""
    if not os.path.exists(DB_PATH):
        createDatabase()

def get_video_info(rss_feed):
    """Return info for all videos found in the given RSS feed.

    Saves to database, if they are not already saved

    Args:
        rss_feed (str): The rss feed to check for videos

    Returns:
        list: List of found videos in format [[url,subject code, video title],...]

    """
    print("Checking RSS feeds...")
    videos = []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    parsed_feed = feedparser.parse(rss_feed[1])

    # check that url is a valid lecture feed
    if not parsed_feed.entries:
        print("{} is not a valid lecture RSS feed".format(rss_feed[1]))

    for entry in parsed_feed.entries:
        # go through the info provided and find the video link
        try:
            enclose = entry.enclosures
            for dictionary in enclose:
                if 'type' in dictionary:
                    if dictionary['type'] == 'video/mp4':
                        url = dictionary['href']

            # regex to find subject code
            codefind = re.findall(r'Course ID:.*?<br', str(entry))
            code = codefind[0][11:-3]

            # get title from rss info
            title = entry.title

            guid = url[41:-14]

            videos.append([url, code, title, guid])

            cursor.execute("INSERT OR IGNORE INTO videos VALUES (?,?,?,0,?,0)", [url, code, title, guid])

        except AttributeError:
            print("Video entry found in RSS, but no link was provided")

    conn.commit()
    conn.close()

    # returns list of all videos found in the rss feed
    return videos

def check_database(videos):
    """Compare a list of given videos to list of videos in database.

    If database does not exist in the specified file directory, it is created.
    Finds videos that have not yet been downloaded, and returns the information
    so that they can be downloaded

    Args:
        videos (list): List of videos in format [[url,subject code, video title],...]

    Returns:
        list: List of videos that have not been downloaded

    """
    print("Checking Database...")
    new_videos = []

    # connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # check to see if the videos have been downloaded
    for item in videos:
        dblist = []
        for row in cursor.execute("SELECT * FROM videos WHERE URL = ? AND Downloaded = 0", [item[0]]):
            dblist.append(row)

        if len(dblist) == 1:
            new_videos.append(item)

    # close connection to database
    conn.commit()
    conn.close()

    # return list of videos with either no database entry, or that have not been downloaded
    return new_videos


def download_progress_bar(count, block_size, total_size):
    """To provide a progress bar to show when downloading LQ videos."""
    percent = int(count*block_size*100/total_size)
    numhash = int(percent/5)
    numdash = int(20 - numhash)
    sys.stdout.write("\r" + "[" + numhash*"#" + numdash*"-" + "] {0}%".format(percent))

    sys.stdout.flush()


def download_from_guid(guid):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM videos WHERE guid = ?", [guid])
    video_info = cursor.fetchall()[0]

    download_video_file(video_info, get_video_path(video_info, '.mp4'))
    mark_db_downloaded(video_info, 'lq')
    return 'no'

def download_video_file(video_info, video_path):
    """Download video file.

    Args:
        - video_info (list): Specifies the video to download, in format
                             [url,subject code, video title]

    """
    # log the video to be downloaded
    print("Downloading {} from subject {}".format(video_info[2], video_info[1]))

    # download video
    URLopener().retrieve(video_info[0], video_path, reporthook=download_progress_bar)
    print("Finished downloading")


def mark_db_downloaded(video_info, quality):
    """Update video in database after downloading.

    Uses database specified in configuration file.

    Args:
        - video_info (list): Specifies the video to mark as downloaded, in format
                             [url,subject code, video title]
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if quality == "lq":
        cursor.execute("UPDATE videos SET `Downloaded` = 1 WHERE `URL` = ?", [video_info[0]])
    else:
        cursor.execute("UPDATE videos SET `Downloaded` = 2 WHERE `URL` = ?", [video_info[0]])

    # close connection to database
    conn.commit()
    conn.close()


def download_all_videos(videos):
    """Download all the videos provided using the download_video_file function.

    Args:
        new_videos (list): List of videos to download
    """
    if HIGH_QUALITY:
        for video_info in videos:
            video_path = get_video_path(video_info, '.mkv')
            print("Downloading {} from subject {} in high quality".format(video_info[2], video_info[1]))
            try:
                flashdownloader.high_quality_download(video_info[0], video_path)
            except:
                video_path = get_video_path(video_info, '.mp4')
                download_video_file(video_info, video_path)
            mark_db_downloaded(video_info, 'hq')
    else:
        for video_info in videos:
            video_path = get_video_path(video_info, '.mp4')
            download_video_file(video_info, video_path)
            mark_db_downloaded(video_info, 'lq')


def get_video_path(video_info, extension):
    """Work out the path that the video needs to be saved to.

    The path that the video needs to be saved to depends on a number of
    options in the configuration file, this function calculates the path.

    Args:
        - video_info (list): Specifies the video to get the path for, in format
                             [url,subject code, video title]
        - extension (str): The file extension to be used for the final video

    Returns:
        - str: The path for the video to be saved to

    """
    video_path = os.path.join(DOWNLOAD_DIRECTORY, video_info[2] + extension)

    # if video files are to be sorted into folders
    if SORT:

        # if subject code directory does not exist, create it
        if not os.path.exists(os.path.join(DOWNLOAD_DIRECTORY, video_info[1])):
            os.makedirs(os.path.join(DOWNLOAD_DIRECTORY, video_info[1]))

        # if to be placed within another folder
        if VIDEO_FOLDER_NAME:
            video_path = os.path.join(DOWNLOAD_DIRECTORY, video_info[1], VIDEO_FOLDER_NAME, video_info[2] + extension)

            # if folder does not exist, create it
            if not os.path.exists(os.path.join(DOWNLOAD_DIRECTORY, video_info[1], VIDEO_FOLDER_NAME)):
                os.makedirs(os.path.join(DOWNLOAD_DIRECTORY, video_info[1], VIDEO_FOLDER_NAME))

        else:
            video_path = os.path.join(DOWNLOAD_DIRECTORY, video_info[1], video_info[2] + extension)

    return video_path


check_database_exists()
# for feed in RSS_FEEDS:
#     videos = get_video_info(feed)
#     new_videos = check_database(videos)
#     download_all_videos(new_videos)
