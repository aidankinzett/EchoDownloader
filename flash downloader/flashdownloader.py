import urllib
from xml.dom import minidom
# get url for files from the url that is given by rss
def getSwfUrl(rssurl):
    return rssurl[:78]

# download the presentation xml file
def getXML(url):
    xml_file = urllib.urlopen(url+"presentation.xml").read()
    xmldoc = minidom.parseString(xml_file)
    

# work out what the highest swf filename is
# highestFileNumber = whatever (integer) <- then use this to loop through all the files

# download the audio file

# download the video files

# convert the video files

# trim the audio file

# smoosh the audio and the video together





# testing

url = "http://lectureplayback.qut.edu.au/1722/4/df2e737e-a09d-4cb9-9176-8847bbb820f1/audio-vga.m4v"
newurl = getSwfUrl(url)
print getXML(newurl)
