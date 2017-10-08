from flask import request, jsonify, render_template, Flask
import sqlite3
import yaml
import os
import subprocess

# open the configuration file and save config as constants
with open("config.yml", 'r') as ymlfile:
    CONFIG = yaml.load(ymlfile)

DOWNLOAD_DIRECTORY = CONFIG['download directory']
DB_PATH = os.path.join(DOWNLOAD_DIRECTORY, 'echodownloader.db')

app = Flask(__name__)

@app.route('/')
def home():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT `Subject Code` FROM urls")
    subjects = cursor.fetchall()

    conn.commit()
    conn.close()
    return render_template('home.html', subjects=subjects)

@app.route('/subject/<subject_code>')
def display_subject(subject_code=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM urls WHERE `Subject Code` = '{}'".format(subject_code))
    videos = cursor.fetchall()

    conn.commit()
    conn.close()

    return render_template('subject.html', videos=videos, subject_code=subject_code)

@app.route('/open/<guid>')
def open_video(guid=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM urls WHERE `GUID` = '{}'".format(guid))
    data = cursor.fetchall()

    conn.commit()
    conn.close()

    file_to_show = os.path.join(DOWNLOAD_DIRECTORY, data[0][1], "Lecture Videos", data[0][2]+".mp4")

    subprocess.call(["open", "-R", file_to_show])

    # make it redirect back a page after opening file
    return render_template('goback.html')
