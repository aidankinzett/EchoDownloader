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

import os

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


@app.route('/settings')
def settings():
    return render_template('settings.html')


@app.route('/subject/<subject_code>')
def display_subject(subject_code=None):

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

    path = video.url

    print(path)

    return render_template('video_player.html', video=video, path=path)