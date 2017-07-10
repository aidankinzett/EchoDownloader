from urllib.request import urlopen, URLopener
from xml.dom import minidom
import os
import ffmpy

# TODO: improve logging and progress bars and stuff

def get_swf_url(rssurl):
    """get url for files from the url that is given by the rss feed"""
    return rssurl[:78]

def get_XML(url):
    """downloads the presentation xml document"""
    xml_file = urlopen(url+"presentation.xml").read()
    xmldoc = minidom.parseString(xml_file)
    return xmldoc

def get_max_time(xmldoc):
    """gets the maximum swf time/filename needed as integer"""
    datas = xmldoc.getElementsByTagName("data")
    max_time = 0
    for data in datas:
        dtype = data.getAttribute("type")
        if dtype == "swf":
            dtime = int(data.getAttribute("time"))
            if dtime > max_time:
                max_time = dtime
    return max_time

def get_guid(xmldoc):
    """gets the guid from the presentation xml document, and creates a folder with that name"""
    guid = str(xmldoc.getElementsByTagName("guid")[0].firstChild.nodeValue)
    # dos.makedirs(guid)
    return guid

def download_swf_video_file(time, url, guid):
    """downloads a single video file from the filename"""
    URLopener().retrieve(url+"/slides/"+'{0:08d}'.format(time)+".swf", guid+"/"
                         +'{0:08d}'.format(time)+".swf")

def download_all_swf_videos(max_time, url, guid):
    """downloads all the videos from time 0 to time max_time"""
    for time in range(0, max_time+1, 8000):
        download_swf_video_file(time, url, guid)

def download_audio_file(url, guid):
    """downloads the audio file for the lecture"""
    URLopener().retrieve(url+"/audio.mp3", guid+"/audio.mp3")

def convert_videos(max_time, guid):
    """converts all the swf files to mkv files"""
    for time in range(0, max_time+1, 8000):
        ff = ffmpy.FFmpeg(
            inputs={guid+"/"+'{0:08d}'.format(time)+'.swf': None},
            outputs={guid+"/"+'{0:08d}'.format(time)+".mkv": None}
            )
        ff.run()
        os.remove(guid+"/"+'{0:08d}'.format(time)+'.swf')

def concat_videos(max_time, guid):
    """concatonates all the videos together, into one video file"""
    # create dictionary of all input files
    input_dict = {}
    for time in range(0, max_time+1, 8000):
        input_dict[guid+"/"+'{0:08d}'.format(time)+'.swf'] = None

    # run FFmpeg
    ff = ffmpy.FFmpeg(
        inputs=input_dict,
        outputs={guid+"/video_output.mkv": '-filter_complex "concat=n={}:v=1 [v] " -map [v]'.format(len(input_dict))}
    )
    ff.run()

    for time in range(0, max_time+1, 8000):
        os.remove(guid+"/"+'{0:08d}'.format(time)+'.swf')

def trim_audio_file(guid):
    """trims the audio file to remove the qut intro sound"""
    ff = ffmpy.FFmpeg(
        inputs={guid+"/audio.mp3":None},
        outputs={guid+"/trimmed_audio.mp3":"-ss 00:00:14 -acodec copy"}
    )
    ff.run()
    os.remove(guid+"/audio.mp3")

def combine_audio_and_video(guid):
    """combines the trimmed audio and the concatonated video files"""
    ff = ffmpy.FFmpeg(
        inputs={guid+"/video_output.mkv": None, guid+"/trimmed_audio.mp3": None},
        outputs={guid+"/final_video.mkv": "-codec copy -shortest"}
    )
    ff.run()

def high_quality_download(url):
    newurl = get_swf_url(url)
    xmldoc = get_XML(newurl)
    max_time = 736000
    guid = get_guid(xmldoc)
    download_all_swf_videos(max_time, newurl, guid)
    download_audio_file(newurl, guid)
    convert_videos(max_time, guid)
    concat_videos(max_time, guid)
    trim_audio_file(guid)
    combine_audio_and_video(guid)
    return guid

high_quality_download("http://lectureplayback.qut.edu.au/1709/4/23e17997-e9cf-4572-9db7-fab2fff8a4bb/presentation.xml")
