import eventlet
import ffmpy
import json
import sqlite3
import subprocess
import sys
from flask import request, render_template, Flask
from flask_socketio import SocketIO, send, emit
from gevent import monkey
from threading import Lock
from urllib.request import URLopener
from urllib.request import urlopen, URLopener
from xml.dom import minidom

import echodownloader
from createDB import *
import feedparser
import re
import webbrowser
import time
import threading

import tasks

monkey.patch_all()

# open the configuration file and save config as constants
with open("config.json", 'r') as ymlfile:
    CONFIG = json.load(ymlfile)
RSS_FEEDS = CONFIG['rss_feeds']

DOWNLOAD_DIRECTORY = os.path.join("static", "videos")
DB_PATH = os.path.join(DOWNLOAD_DIRECTORY, 'echodownloader.db')

app = Flask(__name__)
socketio = SocketIO(app)

async_mode = eventlet

if __name__ == '__main__':
    socketio.run(app, async_mode=async_mode)

thread = None
thread_lock = Lock()

url = 'http://localhost:5000'

print('Go to '+url+' in your web browser')

downloading_guid = ""
downloading_subject = ""
downloading_title = ""
download_queue = []

clean_subjects = ""

current_celery_download = None


@app.route('/')
def home():
    return render_template('home.html', subjects=clean_subjects)


@app.route('/settings', methods=['POST', 'GET'])
def settings():
    with open("config.json", 'r') as ymlfile:
        CONFIG = json.load(ymlfile)
    RSS_FEEDS = CONFIG['rss_feeds']

    if request.method == 'POST':
        print(request.form)
        rss_feeds=[]

        for key, value in request.form.items():
            rss_feeds += [value]

        rss_feeds_sliced = [rss_feeds[i:i+4] for i in range(0, len(rss_feeds), 4)]

        print(rss_feeds_sliced)

        data = {"rss_feeds":rss_feeds_sliced}
        with open('config.json', 'w') as outfile:
            json.dump(data, outfile)

    clean_subjects = []
    for item in RSS_FEEDS:
        clean_subjects.append(item[0])

    return render_template('settings.html', rss_feeds=RSS_FEEDS, subjects=clean_subjects)


@app.route('/subject/<subject_code>')
def display_subject(subject_code=None):
    session = createSession()

    videos = session.query(Video).filter(Video.subject_code == subject_code)

    return render_template('subject.html', videos=videos, subject_code=subject_code, subjects=clean_subjects)


@app.route('/video?=<guid>')
def play_video(guid=None):
    session = createSession()
    video = session.query(Video).filter(Video.guid == guid)[0]

    if video.downloaded == 1:
        path = "videos/" + video.subject_code + "/" + video.title + ".mp4"
    elif video.downloaded == 2:
        path = "videos/" + video.subject_code + "/" + video.title + ".mkv"
    else:
        path = video.url

    print(path)
    return render_template('video_player.html', video=video, path=path, subjects=clean_subjects)


@app.route('/downloads')
def downloads():
    return render_template('downloads.html', subjects=clean_subjects)


def download_progress_bar(count, block_size, total_size):
    global downloading_guid, downloading_subject, downloading_title
    """To provide a progress bar to show when downloading LQ videos."""
    percent = int(count * block_size * 100 / total_size)
    print(percent)
    progress = {'guid': downloading_guid, 'downloading': percent, 'subject': downloading_subject, 'title': downloading_title}
    socketio.emit('downloading', progress)
    socketio.sleep(0.001)


@socketio.on('open_video')
def open_video(guid):
    session = createSession()
    video = session.query(Video).filter(Video.guid == guid)[0]

    if video.downloaded == 1:
        file_to_show = os.path.join(DOWNLOAD_DIRECTORY, video.subject_code, video.title + ".mp4")
    elif video.downloaded == 2:
        file_to_show = os.path.join(DOWNLOAD_DIRECTORY, video.subject_code, video.title + ".mkv")

    subprocess.call(["open", "-R", file_to_show])


@socketio.on('client_connected')
def handle_client_connect_event(json):
    print('received json: {0}'.format(str(json)))
    send('hello client')


@socketio.on('message')
def handle_message(message):
    print('received message: ' + message)


@socketio.on('download')
def emit_download(message):
    global thread, downloading_bool, download_queue
    download_queue.append([message, 0])


@socketio.on('delete')
def delete_video(guid):
    session = createSession()
    video = session.query(Video).filter(Video.guid == guid)[0]

    if video.downloaded == 1:
        os.remove(os.path.join(DOWNLOAD_DIRECTORY, video.subject_code, video.title + ".mp4"))
    elif video.downloaded == 2:
        os.remove(os.path.join(DOWNLOAD_DIRECTORY, video.subject_code, video.title + ".mkv"))

    video.downloaded = 0
    session.commit()


def download_video():
    global downloading_guid, downloading_title, downloading_subject, download_queue, current_celery_download
    while True:
        if len(download_queue) != 0:
            for message in download_queue:
                if message[1] == 0:
                    print(message)
                    download_queue.remove(message)

                    guid = message[0]

                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()

                    cursor.execute("SELECT * FROM videos WHERE guid = ?", [guid])
                    video_info = cursor.fetchall()[0]

                    conn.commit()
                    conn.close()

                    video_path = echodownloader.get_video_path(video_info, '.mp4')
                    # log the video to be downloaded
                    print("Downloading {} from subject {}".format(video_info[2], video_info[1]))
                    downloading_guid = video_info[4]
                    downloading_subject = video_info[1]
                    downloading_title = video_info[2]
                    # download video
                    URLopener().retrieve(video_info[0], video_path, reporthook=download_progress_bar)
                    print("Finished downloading")
                    socketio.emit('downloading', 'done')

                    echodownloader.mark_db_downloaded(video_info, 'lq')
                else:
                    print(message)
                    download_queue.remove(message)
                    current_celery_download = tasks.download_high_quality.delay(message[0])
            socketio.sleep(0.01)
        socketio.sleep(0.01)





@socketio.on('download_hq')
def emit_download_high_quality(message):
    global thread, download_queue
    download_queue.append([message, 1])


@socketio.on('mark_watched')
def mark_video_as_watched(message):
    session = createSession()
    video = session.query(Video).filter(Video.guid == message)[0]
    video.watched = 1
    session.commit()


@socketio.on('mark_unwatched')
def mark_video_as_unwatched(message):
    session = createSession()
    video = session.query(Video).filter(Video.guid == message)[0]
    video.watched = 0
    session.commit()


def get_video_info(rss_feed):
    global download_queue
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

            cursor.execute("SELECT * FROM videos WHERE guid = ?", [guid])
            video_info = cursor.fetchall()[0]

            if video_info[5] == 0:
                if rss_feed[2] == 'on':
                    if rss_feed[3] == 'on':
                        download_queue.append([guid, 1])
                    else:
                        download_queue.append([guid, 0])



        except AttributeError:
            print("Video entry found in RSS, but no link was provided")

    conn.commit()
    conn.close()

    # returns list of all videos found in the rss feed
    return videos


def check_rss_feeds():
    global clean_subjects

    while True:
        with open("config.json", 'r') as ymlfile:
            CONFIG = json.load(ymlfile)
        RSS_FEEDS = CONFIG['rss_feeds']

        for item in RSS_FEEDS:
            get_video_info(item)

        clean_subjects = []
        for item in RSS_FEEDS:
            clean_subjects.append(item[0])

        socketio.sleep(300)


"""
Start two background threads:
    - download_thread: checks the downloa queue and if the previous download has finished, starts the next one
    - check_rss_thread: checks the rss feeds for new videos
"""
download_thread = socketio.start_background_task(target=download_video)
check_rss_thread = socketio.start_background_task(target=check_rss_feeds)