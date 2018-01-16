import sqlite3
import subprocess
import echodownloader
import json
import eventlet
import sys
from threading import Lock
from flask import request, render_template, Flask
from flask_socketio import SocketIO, send, emit

from createDB import *

from urllib.request import URLopener

# open the configuration file and save config as constants
with open("config.json", 'r') as ymlfile:
    CONFIG = json.load(ymlfile)

RSS_FEEDS = CONFIG['rss_feeds']
DOWNLOAD_DIRECTORY = CONFIG['download_directory']
DB_PATH = os.path.join(DOWNLOAD_DIRECTORY, 'echodownloader.db')
HIGH_QUALITY = CONFIG['high_quality']
SORT = CONFIG['sort']
VIDEO_FOLDER_NAME = CONFIG['folder_name']

app = Flask(__name__)
socketio = SocketIO(app)

async_mode = eventlet

if __name__ == '__main__':
    socketio.run(app, async_mode=async_mode)

thread = None
thread_lock = Lock()


@app.route('/')
def home():
    session = createSession()

    subjects = session.query(Video).distinct(Video.subject_code).group_by(Video.subject_code)

    clean_subjects = []
    for subject in subjects:
        clean_subjects.append(subject.subject_code)

    return render_template('home.html', subjects=clean_subjects)


@app.route('/settings', methods=['POST', 'GET'])
def settings():
    if request.method == 'POST':
        data = {
            'rss feeds': [request.form['rss_1'], request.form['rss_2'], request.form['rss_3']],
            'download directory': request.form['download_directory'],
            'folder name within subject folder': request.form['video_folder_name']
        }

        if 'sort' in request.form:
            data['sort into subject folders'] = True
        else:
            data['sort into subject folders'] = False

        if 'high_quality' in request.form:
            data['high quality'] = True
        else:
            data['high quality'] = False
        #
        # with open('config.yml', 'w') as outfile:
        #     yaml.dump(data, outfile, encoding='utf-8', allow_unicode=True)

    with open("config.json", 'r') as ymlfile:
        CONFIG = json.load(ymlfile)

    RSS_FEEDS = CONFIG['rss_feeds']
    DOWNLOAD_DIRECTORY = CONFIG['download_directory']
    DB_PATH = os.path.join(DOWNLOAD_DIRECTORY, 'echodownloader.db')
    HIGH_QUALITY = CONFIG['high_quality']
    SORT = CONFIG['sort']
    VIDEO_FOLDER_NAME = CONFIG['folder_name']
    session = createSession()
    subjects = session.query(Video).distinct(Video.subject_code).group_by(Video.subject_code)

    clean_subjects = []
    for subject in subjects:
        clean_subjects.append(subject.subject_code)

    return render_template('settings.html', rss_feeds=RSS_FEEDS, download_directory=DOWNLOAD_DIRECTORY,
                           high_quality=HIGH_QUALITY,
                           sort=SORT, video_folder_name=VIDEO_FOLDER_NAME, subjects=clean_subjects)


@app.route('/subject/<subject_code>')
def display_subject(subject_code=None):
    for item in RSS_FEEDS:
        if item[0] == subject_code:
            echodownloader.get_video_info(item)
    session = createSession()

    videos = session.query(Video).filter(Video.subject_code == subject_code)

    subjects = session.query(Video).distinct(Video.subject_code).group_by(Video.subject_code)

    clean_subjects = []
    for subject in subjects:
        clean_subjects.append(subject.subject_code)

    return render_template('subject.html', videos=videos, subject_code=subject_code, subjects=clean_subjects)


@app.route('/video?=<guid>')
def play_video(guid=None):
    session = createSession()
    video = session.query(Video).filter(Video.guid == guid)[0]

    if video.downloaded != 0 :
        path = os.path.join(video.subject_code, "Lecture Videos", video.title + ".mp4")
    else:
        path = video.url

    print(path)

    return render_template('video_player.html', video=video, path=path)

def download_progress_bar(count, block_size, total_size):
    """To provide a progress bar to show when downloading LQ videos."""
    percent = int(count*block_size*100/total_size)
    print(percent)
    emit('downloading', percent)
    socketio.sleep(0.001)


@socketio.on('open_video')
def open_video(guid):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM videos WHERE `GUID` = '{}'".format(guid))
    data = cursor.fetchall()

    conn.commit()
    conn.close()

    file_to_show = os.path.join(DOWNLOAD_DIRECTORY, data[0][1], "Lecture Videos", data[0][2] + ".mp4")

    subprocess.call(["open", "-R", file_to_show])


def testing_bullshit():
    send("this is shit")


@socketio.on('client_connected')
def handle_client_connect_event(json):
    print('received json: {0}'.format(str(json)))
    send('hello client')
    testing_bullshit()


@socketio.on('message')
def handle_message(message):
    print('received message: ' + message)


@socketio.on('download')
def emit_download(message):
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=download_video(message))


def download_video(message):
    send('fuck this piece of fucking shit')
    socketio.sleep(0.01)

    guid = message

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM videos WHERE guid = ?", [guid])
    video_info = cursor.fetchall()[0]

    video_path = echodownloader.get_video_path(video_info, '.mp4')
    # log the video to be downloaded
    print("Downloading {} from subject {}".format(video_info[2], video_info[1]))

    # download video
    URLopener().retrieve(video_info[0], video_path, reporthook=download_progress_bar)
    print("Finished downloading")
    socketio.emit('downloading', 'done')

    echodownloader.mark_db_downloaded(video_info, 'lq')