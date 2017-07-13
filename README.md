# EchoDownloader
EchoDownloader is a Python 3 script that checks multiple echo360 lecture recording RSS feeds, downloads any new lectures, then renames and sorts them into subject folders. It can also download videos in high resolution, which is not possible through the website.

## Setup
Requires "vodcast" RSS feed url, found at the bottom left of the subject's Echo360 page. Add RSS feeds to the config.yml configuration file. Run the echodownloader script regularly, such as on a crontab, to keep the downloads up to date. On first run all lectures available in the feed will be downloaded.

### Requirements (install through pip):
- PyYAML
- feedparser
- ffmpy

### Configuration
Configuration is read from the config.yml YAML file.
#### RSS Feeds:
The RSS feeds for the subjects to automatically download lectures from.

#### Download Directory:
The file path to save the videos to.

#### Sort into Subject Folders (Yes/No):
Sort the videos into folders named with the subject code. These folders will be created in the Download Directory.
eg. Download Directory/IFB101/

#### Folder Name within Subject Folders:
The name of the folder to place the videos in within the subject folder. If Sort into Subject Folders is set to no, this option does nothing.
eg. Download Directory/IFB101/Lecture Videos/

#### High Quality (Yes/No):
Download video in higher quality (720p).

## High Quality downloads
High quality downloads require transcoding, so will take more time, and be more CPU intensive than low quality downloads. To download a single video, without using the EchoDownloader RSS checker, call the flashdownloader python file, followed by the URL for the lecture video as a command line argument. This video will be saved to the Download Directory specified in the config file. If the high quality video cannot be found, then the low quality version will be downloaded.
