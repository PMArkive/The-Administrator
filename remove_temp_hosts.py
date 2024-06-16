# Std Lib Imports
import time

# 3rd Party Imports
import databases
import asyncio
import requests

# Local Imports
from utils import load_config

# config
config = load_config()
global_config = config

async def main():

    print("Starting temp-host removal script.")
    database = databases.Database(global_config.databases.tf2maps_site)
    await database.connect()

    # select user_id from xf_user where find_in_set(43, secondary_group_ids)
    query = "SELECT user_id FROM xf_user WHERE find_in_set(43, secondary_group_ids)"
    results = await database.fetch_all(query=query,)

    for user_id in results:
        print(f"Getting secondary groups for {user_id}.")
        user_secondary_groups = await get_user_roles(user_id[0])

        print(f"Removing group from {user_id}.")
        await del_user_hosts(user_id[0], user_secondary_groups)

async def get_user_roles(user_id):
    #
    # Send API request for user groups
    #
    headers = {
        'Content-type': 'application/x-www-form-urlencoded',
        'XF-Api-Key': global_config.apikeys.xenforo.key
    }

    params = {
        'api_bypass_permissions': 1
    }
    url = f'https://tf2maps.net/api/users/{user_id}/'
    r = requests.get(url, headers=headers, params=params)
    jsonR = r.json()
    user_secondary_groups = jsonR['user']['secondary_group_ids']
    return user_secondary_groups

async def del_user_hosts(user_id, user_secondary_groups):
    user_secondary_groups.remove(43)
    headers = {
        'Content-type': 'application/x-www-form-urlencoded',
        'XF-Api-Key': global_config.apikeys.xenforo.key
    }
    params = {
        'api_bypass_permissions': 1
    }
    data = {
        'secondary_group_ids[]': [user_secondary_groups],
    }
    url = f'https://tf2maps.net/api/users/{user_id}/'
    r = requests.post(url, headers=headers, params=params, data=data)
    if r.status_code == 200:
        print(f"Removed from temp-host group")
        time.sleep(2)
        return

    print(f"Unable to remove them from the role.")
    return

# loooooop
loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(main())
except KeyboardInterrupt:
    pass
finally:
    loop.stop()
