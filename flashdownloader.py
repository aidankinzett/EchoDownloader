"""Download higher quality videos from Echo360.

From a given URL can download the individual .swf file, convert and stitch
them together. Also downloads the audio file, and adds that to the video.

Include the URL for the lecture as a command line argument when running the script.
The video will be saved in the download directory specified in the configuration file,
named with the GUID. The URL to use can be found in the RSS feed for the lecture.

Example URL: ...
Does not work with URLs like: ...

Todo:
    * Progress bars and console logs
    * Maybe add the QUT intro to the videos
    * Replace / with os.path.join, cause this wont work on windows
    * Restructure how the video path works, so that when run from the command
      line, it saves with the correct name.
"""
from urllib.request import urlopen, URLopener
from xml.dom import minidom
import os
import sys
import ffmpy
import yaml

# open the configuration file and save config as constants
with open("config.yml", 'r') as ymlfile:
    CONFIG = yaml.load(ymlfile)

DOWNLOAD_DIRECTORY = CONFIG['download directory']

def get_swf_url(rssurl):
    """Get url for files from the url that is given by the rss feed.

    Args:
        - rssurl (str): The URL given by the rss feed

    Returns:
        - str: base URL for lecture, to be used with other functions in this module

    """
    return rssurl[:78]

def get_xml(url):
    """Download the presentation xml document.

    Args:
        - url (str): The base url for the lecture

    Returns:
        - obj: The minidom object of the xml document for the lecture

    """
    xml_file = urlopen(url+"presentation.xml").read()
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
    if not os.path.exists(DOWNLOAD_DIRECTORY+"/"+guid):
        os.makedirs(DOWNLOAD_DIRECTORY+"/"+guid)
    return guid

def download_swf_video_file(time, url, guid):
    """Download single swf video file.

    The download is stored in the temporary folder named using the GUID

    Args:
        - time (int): Time code to be downloaded
        - url (str): The lecture's base url
        - guid (str): The lecture's guid

    """
    URLopener().retrieve(url+"/slides/"+'{0:08d}'.format(time)+".swf", DOWNLOAD_DIRECTORY
                         + "/" + guid +"/" + '{0:08d}'.format(time)+".swf", reporthook=download_progress_bar)

def download_progress_bar(count, block_size, total_size):
    """To provide a progress bar to show when downloading files."""
    percent = int(count*block_size*100/total_size)
    numhash = int(percent/5)
    numdash = int(20 - numhash)
    sys.stdout.write("\r" + "[" + numhash*"#" + numdash*"-" + "] {0}%".format(percent))

    sys.stdout.flush()

def download_all_swf_videos(max_time, url, guid):
    """Download all the videos from time 0 to time max_time.

    The downloads are stored in the tempoary folder named using the GUID

    Args:
        - max_time (int): The maximum time code that needs to be downloaded
        - url (str): The lecture's base url
        - guid (str): The lecture's guid
    """
    for time in range(0, max_time+1, 8000):
        print("\nDownloading file {} of {}...".format(str(time/8000+1), str(max_time/8000+1)))
        download_swf_video_file(time, url, guid)

def download_audio_file(url, guid):
    """Download the audio file for the lecture.

    Downloads the mps audio recording of the lecture. File is stored in the
    tempoary folder named using the GUID

    Args:
        - url (str): The lecture's base url
        - guid (str): The lecture's guid

    """
    print("Downloading audio file")
    URLopener().retrieve(url+"/audio.mp3", DOWNLOAD_DIRECTORY + "/" + guid+"/audio.mp3", reporthook=download_progress_bar)

def convert_videos(max_time, guid):
    """Convert all the swf files to mkv files.

    Converts swf videos from time 0 to time max_time contained within the GUID folder
    to mkv videos. Deletes the old swf files.

    Args:
        - max_time (int): The maximum time code that needs to be downloaded
        - guid (str): The lecture's guid
    """
    for time in range(0, max_time+1, 8000):
        ff_command = ffmpy.FFmpeg(
            inputs={DOWNLOAD_DIRECTORY + "/" + guid+"/"+'{0:08d}'.format(time)+'.swf': None},
            outputs={DOWNLOAD_DIRECTORY + "/" + guid+"/"+'{0:08d}'.format(time)+".mkv": None}
            )
        ff_command.run()
        os.remove(DOWNLOAD_DIRECTORY + "/" + guid+"/"+'{0:08d}'.format(time)+'.swf')

def concat_videos(max_time, guid):
    """Concatonate all the videos together, into one video file.

    Joins together videos from time 0 to max_time contained within the GUID
    folder. Deletes the tempoary video files.

    Args:
        - max_time (int): The maximum time code that needs to be downloaded
        - guid (str): The lecture's guid

    """
    # create dictionary of all input files
    input_dict = {}
    for time in range(0, max_time+1, 8000):
        input_dict[DOWNLOAD_DIRECTORY + "/" + guid+"/"+'{0:08d}'.format(time)+'.mkv'] = None

    # run FFmpeg
    ff_command = ffmpy.FFmpeg(
        inputs=input_dict,
        outputs={
            DOWNLOAD_DIRECTORY + "/" + guid+"/video_output.mkv":
            '-filter_complex "concat=n={}:v=1 [v] " -map [v]'.format(len(input_dict))
            }
    )
    ff_command.run()

    for time in range(0, max_time+1, 8000):
        os.remove(DOWNLOAD_DIRECTORY + "/" + guid+"/"+'{0:08d}'.format(time)+'.mkv')

def trim_audio_file(guid):
    """Trims the audio file to remove the qut intro sound.

    Trims the audio file name "audio.mp3" contained within the GUID folder to
    remove the first 15 seconds.

    Args:
        - guid (str): The lecture's guid
    """
    ff_command = ffmpy.FFmpeg(
        inputs={DOWNLOAD_DIRECTORY + "/" + guid+"/audio.mp3":None},
        outputs={DOWNLOAD_DIRECTORY + "/" + guid+"/trimmed_audio.mp3":"-ss 00:00:15 -acodec copy"}
    )
    ff_command.run()
    os.remove(DOWNLOAD_DIRECTORY + "/" + guid+"/audio.mp3")

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
        inputs={DOWNLOAD_DIRECTORY + "/" + guid+"/video_output.mkv": None, DOWNLOAD_DIRECTORY
                + "/" + guid+"/trimmed_audio.mp3": None},
        outputs={video_path: "-codec copy -shortest"}
    )
    ff_command.run()
    os.remove(DOWNLOAD_DIRECTORY + "/" + guid + "/video_output.mkv")
    os.remove(DOWNLOAD_DIRECTORY + "/" + guid + "/trimmed_audio.mp3")
    os.rmdir(DOWNLOAD_DIRECTORY + "/" + guid)

def high_quality_download(url, video_path):
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
    download_all_swf_videos(max_time, newurl, guid)
    download_audio_file(newurl, guid)
    convert_videos(max_time, guid)
    concat_videos(max_time, guid)
    trim_audio_file(guid)
    combine_audio_and_video(guid, video_path)

if len(sys.argv) != 2 and sys.argv[:-19] == "flashdownloader.py":
    print("Enter url for lecture as a command line argument")
elif sys.argv[:-19] == "flashdownloader.py":
    url = sys.argv[1]
    newurl = get_swf_url(url)
    xmldoc = get_xml(newurl)
    guid = get_guid(xmldoc)
    try:
        high_quality_download(sys.argv[1], DOWNLOAD_DIRECTORY+"/"+guid+".mkv")
    except:
        URLopener().retrieve(sys.argv[1], DOWNLOAD_DIRECTORY+"/"+guid+".mp4")
