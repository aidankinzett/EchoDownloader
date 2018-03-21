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
downloading_bool = False
download_queue = []

clean_subjects = ""

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
    global downloading_guid, downloading_title, downloading_subject, downloading_bool, download_queue
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
                    download_high_quality(message[0])
            socketio.sleep(0.01)
        socketio.sleep(0.01)

thread = socketio.start_background_task(target=download_video)




@socketio.on('download_hq')
def emit_download_high_quality(message):
    global thread, downloading_bool, download_queue
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


def download_high_quality(message):
    global thread, downloading_bool
    socketio.sleep(0.01)
    guid = message

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM videos WHERE guid = ?", [guid])
    video_info = cursor.fetchall()[0]

    video_path = echodownloader.get_video_path(video_info, '.mkv')
    print("Downloading {} from subject {} in high quality".format(video_info[2], video_info[1]))
    high_quality_download(video_info[0], video_path, video_info[1], video_info[2])

    echodownloader.mark_db_downloaded(video_info, 'hq')
    downloading_bool = False


def get_swf_url(rssurl):
    """Get url for files from the url that is given by the rss feed.

    Args:
        - rssurl (str): The URL given by the rss feed

    Returns:
        - str: base URL for lecture, to be used with other functions in this module

    """
    if rssurl[:4] == "https":
        return rssurl[:79]
    else:
        return rssurl[:78]


def get_xml(url):
    """Download the presentation xml document.

    Args:
        - url (str): The base url for the lecture

    Returns:
        - obj: The minidom object of the xml document for the lecture

    """
    xml_file = urlopen(url + "presentation.xml").read()
    xmldoc = minidom.parseString(xml_file)
    return xmldoc


def get_max_time(xmldoc):
    """Get the maximum swf time/filename needed as integer.

    Args:
        - xmldoc (obj): The minidom object for the lecture's xml document

    Returns:
        - int: The largest time code from the lecture

    """
    datas = xmldoc.getElementsByTagName("data")
    max_time = 0
    for data in datas:
        dtype = data.getAttribute("type")
        if dtype == "swf":
            dtime = int(data.getAttribute("time"))
            if dtime > max_time:
                max_time = dtime
    return max_time


def get_title(xmldoc):
    title = str(xmldoc.getElementsByTagName("name")[0].firstChild.nodeValue)
    return title


def get_guid(xmldoc):
    """Get the guid from the presentation xml document.

    The guid is a unique identifier for the lecture. Temporary files for the
    download are stored in a folder named with the guid.

    Args:
        - xmldoc (obj): The minidom object for the lecture's xml document

    Returns:
        - str: The lecture's guid, a unique identifier

    """
    guid = str(xmldoc.getElementsByTagName("guid")[0].firstChild.nodeValue)
    if not os.path.exists(os.path.join(DOWNLOAD_DIRECTORY, guid)):
        os.makedirs(os.path.join(DOWNLOAD_DIRECTORY, guid))
    return guid


def download_swf_video_file(time, url, guid):
    """Download single swf video file.

    The download is stored in the temporary folder named using the GUID

    Args:
        - time (int): Time code to be downloaded
        - url (str): The lecture's base url
        - guid (str): The lecture's guid

    """
    URLopener().retrieve(url + "/slides/" + '{0:08d}'.format(time) + ".swf",
                         os.path.join(DOWNLOAD_DIRECTORY, guid, '{0:08d}'.format(time) + ".swf"))


def download_all_swf_videos(max_time, url, guid, subject, title):
    """Download all the videos from time 0 to time max_time.

    The downloads are stored in the tempoary folder named using the GUID

    Args:
        - max_time (int): The maximum time code that needs to be downloaded
        - url (str): The lecture's base url
        - guid (str): The lecture's guid
    """
    for time in range(0, max_time + 1, 8000):
        socketio.sleep(0.01)
        print("\nDownloading video file {:.0f} of {:.0f}...".format(time / 8000 + 1, max_time / 8000 + 1))
        download_swf_video_file(time, url, guid)

        percentage = (time / 8000 + 1) / (max_time / 8000 + 1) * 100
        progress = {'guid': guid, 'downloading': percentage, 'converting': 0, 'subject':subject, 'title':title}
        socketio.emit('downloading_hq', progress)
        socketio.sleep(0.01)


def download_audio_file(url, guid):
    """Download the audio file for the lecture.

    Downloads the mps audio recording of the lecture. File is stored in the
    tempoary folder named using the GUID

    Args:
        - url (str): The lecture's base url
        - guid (str): The lecture's guid

    """
    print("\nDownloading audio file")
    URLopener().retrieve(url + "/audio.mp3", os.path.join(DOWNLOAD_DIRECTORY, guid, "audio.mp3"))


def convert_videos(max_time, guid, subject, title):
    """Convert all the swf files to mkv files.

    Converts swf videos from time 0 to time max_time contained within the GUID folder
    to mkv videos. Deletes the old swf files.

    Args:
        - max_time (int): The maximum time code that needs to be downloaded
        - guid (str): The lecture's guid
    """
    for time in range(0, max_time + 1, 8000):
        ff_command = ffmpy.FFmpeg(
            inputs={os.path.join(DOWNLOAD_DIRECTORY, guid, '{0:08d}'.format(time) + '.swf'): None},
            outputs={os.path.join(DOWNLOAD_DIRECTORY, guid, '{0:08d}'.format(time) + ".mkv"): None}
        )
        ff_command.run()
        os.remove(os.path.join(DOWNLOAD_DIRECTORY, guid, '{0:08d}'.format(time) + '.swf'))

        percentage = (time / 8000 + 1) / (max_time / 8000 + 1) * 100
        progress = {'guid': guid, 'downloading': 100, 'converting': percentage, 'subject':subject, 'title':title}
        socketio.emit('downloading_hq', progress)
        socketio.sleep(0.01)


def concat_videos(max_time, guid):
    """Concatonate all the videos together, into one video file.

    Joins together videos from time 0 to max_time contained within the GUID
    folder. Deletes the tempoary video files.

    Args:
        - max_time (int): The maximum time code that needs to be downloaded
        - guid (str): The lecture's guid

    """
    # create text file of all input files
    file = open(os.path.join(DOWNLOAD_DIRECTORY, guid, "input.txt"), "w")

    for time in range(0, max_time + 1, 8000):
        socketio.sleep(0.001)
        file.write("file '" + os.path.join('{0:08d}'.format(time)) + ".mkv'\n")

    file.close()

    # run FFmpeg
    ff_command = ffmpy.FFmpeg(
        inputs={
            os.path.join(DOWNLOAD_DIRECTORY, guid, "input.txt"): "-f concat -safe 0"
        },
        outputs={
            os.path.join(DOWNLOAD_DIRECTORY, guid, "video_output.mkv"): "-codec copy"
        }
    )
    ff_command.run()

    for time in range(0, max_time + 1, 8000):
        socketio.sleep(0.001)
        os.remove(os.path.join(DOWNLOAD_DIRECTORY, guid, '{0:08d}'.format(time) + '.mkv'))

    os.remove(os.path.join(DOWNLOAD_DIRECTORY, guid, "input.txt"))


def trim_audio_file(guid):
    """Trims the audio file to remove the qut intro sound.

    Trims the audio file name "audio.mp3" contained within the GUID folder to
    remove the first 15 seconds.

    Args:
        - guid (str): The lecture's guid
    """
    ff_command = ffmpy.FFmpeg(
        inputs={os.path.join(DOWNLOAD_DIRECTORY, guid, "audio.mp3"):None},
        outputs={os.path.join(DOWNLOAD_DIRECTORY, guid, "trimmed_audio.mp3"):"-ss 00:00:15 -acodec copy"}
    )
    ff_command.run()

    ff_command2 = ffmpy.FFmpeg(
        inputs={os.path.join(DOWNLOAD_DIRECTORY, guid, "trimmed_audio.mp3"): None},
        outputs={os.path.join(DOWNLOAD_DIRECTORY, guid, "synced_audio.mp3"): '-filter:a atempo="0.9950835791"'}
    )
    ff_command2.run()

    os.remove(os.path.join(DOWNLOAD_DIRECTORY, guid, "audio.mp3"))
    os.remove(os.path.join(DOWNLOAD_DIRECTORY, guid, "trimmed_audio.mp3"))


def combine_audio_and_video(guid, video_path):
    """Combine the trimmed audio and the concatonated video files.

    Combines the video file named "video_output.mkv" and the audio file
    named "trimmed_audio.mp3", found within the GUID folder.

    Args:
        - guid (str): The lecture's guid
        - video_path (str): The path for the final video to be saved to

        video_path also requires the file name and extension.
    """
    ff_command = ffmpy.FFmpeg(
        inputs={os.path.join(DOWNLOAD_DIRECTORY, guid, "video_output.mkv"): None,
                os.path.join(DOWNLOAD_DIRECTORY, guid, "synced_audio.mp3"): None},
        outputs={video_path: "-codec copy -shortest"}
    )
    ff_command.run()
    os.remove(os.path.join(DOWNLOAD_DIRECTORY, guid, "video_output.mkv"))
    os.remove(os.path.join(DOWNLOAD_DIRECTORY, guid, "synced_audio.mp3"))
    os.rmdir(os.path.join(DOWNLOAD_DIRECTORY, guid))


def high_quality_download(url, video_path, subject, title):
    """Download a lecture from Echo360 in high quality.

    Given the url provided by the RSS feed for a lecture recording, this function
    will download the recording in HD and save it to the specified video path.

    Args:
        - url (str): The lecture's base url
        - video_path (str): The path for the final video to be saved to

    """
    newurl = get_swf_url(url)
    xmldoc = get_xml(newurl)
    max_time = get_max_time(xmldoc)
    guid = get_guid(xmldoc)
    download_all_swf_videos(max_time, newurl, guid, subject, title)
    download_audio_file(newurl, guid)
    convert_videos(max_time, guid, subject, title)
    concat_videos(max_time, guid)
    trim_audio_file(guid)
    combine_audio_and_video(guid, video_path)

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


thread = socketio.start_background_task(target=check_rss_feeds)