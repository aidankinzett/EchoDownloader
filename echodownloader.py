from urllib.request import urlopen, URLopener
import feedparser
import re
import sqlite3
import sys
import os

## List of subject feeds to check
feeds = ["https://example.com/feed.rss"]

## Path to folder to save videos in
path = "/example/path"

## Create Empty Lists
newVideos = []

debug = False

## Returns the URLS of all videos for subjects in a list in format [[url,subject code, video title],...]
def getVideoURLs():
    print("Checking RSS feeds for videos...")

    videos = []

    for item in feeds:
        subjectRSS = feedparser.parse(item)
        for e in subjectRSS.entries:
            codefind = re.findall(r'Course ID:.*?<br',str(e))
            code = codefind[0][11:-3]

            title = e.title

            enclose = e.enclosures
            for dictionary in enclose:
                if 'type' in dictionary:
                    if dictionary['type'] == 'video/mp4':
                        url = dictionary['href']

            videos.append([url,code,title])

    if debug:
        print("Found {0} videos".format(len(videos)))

    return videos

def dlProgress(count, blockSize, totalSize):
    global rem_file
    percent = int(count*blockSize*100.0/totalSize)
    numhash = percent/5
    numdash = 20 - numhash
    sys.stdout.write("\r" + "Downloading " + rem_file + "... [" + numhash*"#" + numdash*"-" + "] {0}%".format(percent))

    sys.stdout.flush()

def downloadVideos(newVideos):

    global rem_file

    sys.stdout.write("%s videos need downloading" % len(newVideos))
    sys.stdout.flush()
    videosDone = 0

    for item in newVideos:
        rem_file = item[2]

        if not os.path.exists(path+item[1]): # checks to see if directory with subject code exists, if not create it
            os.makedirs(path+'/'+item[1])

        if not os.path.exists(path+item[1]+'/Lecture Videos'): # checks to see if lecture videos folder exists, if not create it
            os.makedirs(path+item[1]+'/Lecture Videos')

        videofile = URLopener()
        videofile.retrieve(item[0],path + item[1] + '/Lecture Videos/' + item[2] +'.mp4', reporthook=dlProgress)

        videosDone += 1
        sys.stdout.write("\n{0} of {1} videos have finished downloading\n".format(videosDone, len(newVideos)))
        sys.stdout.flush()


        # Save video in database after downloading
        conn = sqlite3.connect('echodownloader.db')
        c = conn.cursor()

        c.execute("INSERT INTO urls VALUES (?,?,?)", item)

        conn.commit()
        conn.close()

# Compares list of given videos to videos in database, takes format [[url,subject code, video title],...]
def checkDatabase(videos):
    newVideos = []

    if not os.path.exists('echodownloader.db'):
        conn = sqlite3.connect('echodownloader.db')
        c = conn.cursor()
        c.execute('CREATE TABLE "urls" ( `URL` TEXT, `Subject Code` TEXT, `Title` TEXT )')

    conn = sqlite3.connect('echodownloader.db')
    c = conn.cursor()

    for item in videos:
        dblist = []
        for row in c.execute("SELECT * FROM urls WHERE URL = ?", [item[0]]):
            dblist.append(row)

        if len(dblist) < 1:
            newVideos.append(item)

    conn.commit()
    conn.close()

    return newVideos

videos = getVideoURLs()
newVideos = checkDatabase(videos)
downloadVideos(newVideos)
