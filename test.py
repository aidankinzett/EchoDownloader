import sqlite3
import yaml
import os

# open the configuration file and save config as constants
with open("config.yml", 'r') as ymlfile:
    CONFIG = yaml.load(ymlfile)

DOWNLOAD_DIRECTORY = CONFIG['download directory']
DB_PATH = os.path.join(DOWNLOAD_DIRECTORY, 'echodownloader.db')



conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT * FROM urls WHERE `Subject Code` = 'MXB102'")
videos = cursor.fetchall()
print(videos)
