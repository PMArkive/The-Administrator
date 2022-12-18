# Std Lib Imports
import os
import datetime
from datetime import datetime
import sys
import asyncio

# 3rd Party Imports
import discord
import databases
import feedparser
import requests

# Local Imports
from utils import load_config

#config
config = load_config()

feed_url = "https://tf2maps.net/forums/-/index.rss"

blog_feed = feedparser.parse(feed_url)
posts = blog_feed.entries

#checks if the link exists in the DB
async def check_if_posted_before(database, link):

    query = "SELECT link FROM postfeed WHERE link = :field_value"
    values = {"field_value": link}

    result = await database.fetch_one(query=query, values=values)
    return result

#check time posted
async def check_time_posted(database, link):
    
    query = "SELECT CONVERT(added, char) FROM postfeed WHERE link = :link_value ORDER BY id DESC"
    values = {
        "link_value": link
    }
    
    result = await database.fetch_one(query=query, values=values)
    return result

#insert into DB
async def insert_into_db(database, title, link, author):
    #format datetime now
    format = "%Y-%m-%d %H:%M:%S"
    now = datetime.now()

    added = now.strftime(format)

    query = "INSERT INTO postfeed (title, link, author, added) VALUES (:title_insert, :url_link, :author_insert, :datetime_insert);"
    values = {
        "title_insert": title,
        "url_link": link,
        "author_insert": author,
        "datetime_insert": added
        }

    result = await database.fetch_one(query=query, values=values)
    return

#post to discord webhook
#insert into db
#insert title, link, author, time added
async def main():

    s = sys.stdout

    database = databases.Database(config.databases.tf2maps_bot)
    await database.connect()

    for entry in posts:

        #check if it was posted before
        if not await check_if_posted_before(database, entry.link):
            s.write(str(datetime.now()) + f" - Found new post {entry.link}.\n")
            #post webhook to discord if not posted before
            data = {
                "content" : f"> New forum post by {entry.author}: \n{entry.link}",
                "username" : "Mecha Engineer"
            }
            try:
                result = requests.post(config['rss_webhook_url'], json=data)
                result.raise_for_status()

                #insert into DB
                await insert_into_db(database, entry.title, entry.link, entry.author)
                s.write(str(datetime.now()) + f" - Inserting new post into DB.\n")
            except:
                s.write(str(datetime.now()) + f" - Too many requests to discord! Trying again in 1 minute.\n")

        #its a reply then
        else:

            #convert rss time stamp to usable format
            entry_time_string = entry.published
            format = "%a, %d %b %Y %H:%M:%S %z"
            entry_time_object = datetime.strptime(entry_time_string, format)

            #get time from DB
            database_time = await check_time_posted(database, entry.link)

            #convert it to something nice
            database_string = str(database_time[0])
            database_format = "%Y-%m-%d %H:%M:%S"
            database_time_object = datetime.strptime(database_string, database_format)

            #check the time differences
            if await time_differences(entry_time_object, database_time_object) is True:
                s.write(str(datetime.now()) + f" - Found new reply on {entry.link}.\n")
                data = {
                    "content" : f"> New reply on **{entry.title}**: \n{entry.link}",
                    "username" : "Mecha Engineer"
                }
                try:
                    result = requests.post(config['rss_webhook_url'], json=data)
                    result.raise_for_status()

                    #insert into DB
                    await insert_into_db(database, entry.title, entry.link, entry.author)
                    s.write(str(datetime.now()) + f" - Inserting reply in thread.\n")
                except:
                    s.write(str(datetime.now()) + f" - Too many requests to discord! Trying again in 1 minute.\n")

    s.flush()

#this checks the time differences between what the rss is reporting and what we have stored in the db
#if there is a newer time in the rss feed and older in the db it posts a new webhook and inserts
async def time_differences(entry_time_object, database_time_object):
    i = 1
    while i > 0:
        if(entry_time_object.year < database_time_object.year):
            return False
        if(entry_time_object.month < database_time_object.month):
            return False
        if(entry_time_object.day < database_time_object.day):
            return False
        if(entry_time_object.hour < database_time_object.hour):
            return False
        if(entry_time_object.minute < database_time_object.minute):
            return False

        return True                                    

#loooooop
loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(main())
except KeyboardInterrupt:
    pass
finally:
    loop.stop()
