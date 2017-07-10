"""
Download videos from Echo360 recordings.

Functions to:
    - Import config from YAML
    - Check RSS feeds
    - Check database
    - Download in LQ
    - Move and rename files (including HQ from flash downloader)

Uses configuration from "config.yml"

Todo:
    * Add error handling
    * More comments
"""
import os
import re
import sqlite3
import sys
from urllib.request import URLopener
import yaml
import feedparser



# open the configuration file and save config as constants
with open("config.yml", 'r') as ymlfile:
    CONFIG = yaml.load(ymlfile)

RSS_FEEDS = CONFIG['rss feeds']
DOWNLOAD_DIRECTORY = CONFIG['download directory']
DB_PATH = DOWNLOAD_DIRECTORY + '/echodownloader.db'
HIGH_QUALITY = CONFIG['high quality']
SORT = CONFIG['sort into subject folders']
VIDEO_FOLDER_NAME = CONFIG['folder name within subject folder']

def check_database_exists():
    """If the database doesnt exists in the specified folder, create one."""
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE "urls" (`URL` TEXT, `Subject Code` TEXT,'+
                       '`Title` TEXT , `Downloaded` INTEGER, UNIQUE(`URL`))')

def get_video_info(rss_feed):
    """Return info for all videos found in the given RSS feed.

    Saves to database, if they are not already saved

    Args:
        rss_feed (str): The rss feed to check for videos

    Returns:
        list: List of found videos in format [[url,subject code, video title],...]

    """
    videos = []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    parsed_feed = feedparser.parse(rss_feed)
    for entry in parsed_feed.entries:
        # regex to find subject code
        codefind = re.findall(r'Course ID:.*?<br', str(entry))
        code = codefind[0][11:-3]

        # get title from rss info
        title = entry.title

        # go through the info provided and find the video link
        enclose = entry.enclosures
        for dictionary in enclose:
            if 'type' in dictionary:
                if dictionary['type'] == 'video/mp4':
                    url = dictionary['href']

        videos.append([url, code, title])

        cursor.execute("INSERT OR IGNORE INTO urls VALUES (?,?,?,0)", [url, code, title])

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
    new_videos = []

    # connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # check to see if the videos have been downloaded
    for item in videos:
        dblist = []
        for row in cursor.execute("SELECT * FROM urls WHERE URL = ? AND Downloaded = 0", [item[0]]):
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

def download_video_file(video_info):
    """Download video file.

    Args:
        - video_info (list): Specifies the video to download, in format
                             [url,subject code, video title]

    """
    # log the video to be downloaded
    print("Downloading {} from subejct {}".format(video_info[2], video_info[1]))

    video_path = DOWNLOAD_DIRECTORY + '/' + video_info[2] + '.mp4'

    # if video files are to be sorted into folders
    if SORT:

        # if subject code directory does not exist, create it
        if not os.path.exists(DOWNLOAD_DIRECTORY+'/'+video_info[1]):
            os.makedirs(DOWNLOAD_DIRECTORY+'/'+video_info[1])

        # if to be placed within another folder
        if VIDEO_FOLDER_NAME:
            video_path = DOWNLOAD_DIRECTORY + '/' + video_info[1] + '/' + VIDEO_FOLDER_NAME + '/' + video_info[2] + '.mp4'

            # if folder does not exist, create it
            if not os.path.exists(DOWNLOAD_DIRECTORY+'/'+video_info[1]+'/'+VIDEO_FOLDER_NAME):
                os.makedirs(DOWNLOAD_DIRECTORY+'/'+video_info[1]+'/'+VIDEO_FOLDER_NAME)

        else:
            video_path = DOWNLOAD_DIRECTORY + '/' + video_info[1] + '/' + video_info[2] + '.mp4'

    # download video
    URLopener().retrieve(video_info[0], video_path, reporthook=download_progress_bar)
    print("Finished downloading")

    # update video in database after downloading
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("UPDATE urls SET `Downloaded` = 1 WHERE `URL` = ?", [video_info[0]])

def download_all_videos(videos):
    """Download all the videos provided using the download_video_file function.

    Args:
        new_videos (list): List of videos to download
    """
    for video in videos:
        download_video_file(video)

check_database_exists()
for feed in RSS_FEEDS:
    download_all_videos(check_database(get_video_info(feed)))
