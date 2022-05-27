# Std Lib Imports
import os
import datetime
import sys

# 3rd Party Imports
import discord
import databases

# Local Imports
from utils import load_config

#intents
intents = discord.Intents.default()
intents.members = True
intents.guilds = True

#config
config = load_config()

#bot
bot = discord.Bot(debug_guilds=[config.guild_id], intents=intents)

@bot.event
async def on_ready():

    #create log file
    s = sys.stdout
    s.write(str(datetime.datetime.now()) + " - Cronjob started.\n")

    print(str(datetime.datetime.now()) + f" - {bot.user} cronjob is running.")

    guild = bot.get_guild(config.guild_id)

    #get the vip object
    vip = discord.utils.get(guild.roles, name="VIP")

    #db connection
    database = databases.Database(config.databases.tf2maps_site)
    await database.connect()

    #check the members under that role
    for member in vip.members:
        
        #check DB
        query = "SELECT provider_key FROM xf_user INNER JOIN xf_user_connected_account ON xf_user.user_id = xf_user_connected_account.user_id WHERE find_in_set(19, secondary_group_ids) AND provider = 'th_cap_discord' AND provider_key = :provider_key;"
        values = {"provider_key": member.id}
        result = await database.fetch_one(query=query, values=values)

        #if not in query remove vip role
        if not result:

            s.write(str(datetime.datetime.now()) + " - Vip expired for: " + str(member) + "\n")

            #remove role
            await member.remove_roles(vip)

            #send them a DM notifying if the expiration
            try:
                await member.send("Your VIP status has expired. Upgrade to VIP https://tf2maps.net/account/upgrades")
            except:
                s.write(str(datetime.datetime.now()) + " - Cannot send notification to: " + str(member) + "\n")

    #lastly check for any members in the discord who are vip on the site but do not have it in the discord, assuming their profile is connected
    query = "SELECT provider_key FROM xf_user INNER JOIN xf_user_connected_account ON xf_user.user_id = xf_user_connected_account.user_id WHERE find_in_set(19, secondary_group_ids) AND provider = 'th_cap_discord'"
    result = await database.fetch_all(query=query)
    for linked_id in result:

        member = guild.get_member(int(linked_id[0]))

        #check if the member is even in the discord before wasting our time
        if member:

            #check if vip is part of their roles
            if vip in member.roles:
                #log they already have the role
                s.write(str(datetime.datetime.now()) + " - " + str(member) + " already has VIP.\n")
            else:
                #log we are giving them the role
                s.write(str(datetime.datetime.now()) + " - " + str(member) + " doesn't have VIP. Assigning.\n")

                await member.add_roles(vip)
                try:
                    await member.send("Saw that you didn't have VIP on the TF2Maps discord server. I went ahead and gave you the role. Thanks for supporting the community!")
                except:
                    s.write(str(datetime.datetime.now()) + " - Cannot send notification to: " + str(member) + "\n")


    s.write(str(datetime.datetime.now()) + " - Cronjob ended.\n")
    os._exit(os.EX_OK)

bot.run(config.cronjob_token)
