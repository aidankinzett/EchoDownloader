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