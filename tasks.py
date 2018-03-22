from celery import Celery
import sqlite3
import json
import os
import echodownloader
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

app = Celery('tasks', backend='rpc://', broker='pyamqp://guest@localhost//')


with open("config.json", 'r') as ymlfile:
    CONFIG = json.load(ymlfile)
RSS_FEEDS = CONFIG['rss_feeds']

DOWNLOAD_DIRECTORY = os.path.join("static", "videos")
DB_PATH = os.path.join(DOWNLOAD_DIRECTORY, 'echodownloader.db')


@app.task
def download_high_quality(message):
    guid = message

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM videos WHERE guid = ?", [guid])
    video_info = cursor.fetchall()[0]

    video_path = echodownloader.get_video_path(video_info, '.mkv')
    print("Downloading {} from subject {} in high quality".format(video_info[2], video_info[1]))
    high_quality_download(video_info[0], video_path, video_info[1], video_info[2])

    echodownloader.mark_db_downloaded(video_info, 'hq')


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
        print("\nDownloading video file {:.0f} of {:.0f}...".format(time / 8000 + 1, max_time / 8000 + 1))
        download_swf_video_file(time, url, guid)

        percentage = (time / 8000 + 1) / (max_time / 8000 + 1) * 100
        progress = {'guid': guid, 'downloading': percentage, 'converting': 0, 'subject':subject, 'title':title}
        # socketio.emit('downloading_hq', progress)


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
        # socketio.emit('downloading_hq', progress)



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