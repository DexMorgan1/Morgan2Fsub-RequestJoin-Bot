#(©)CodeXBotz

import pymongo
from config import (
    DB_URI,
    DB_NAME,
    FORCE_SUB_CHANNEL,
    FORCE_SUB_CHANNEL2,
    FORCE_SUB_CHANNEL_ENABLED,
    FORCE_SUB_CHANNEL2_ENABLED,
)


dbclient = pymongo.MongoClient(DB_URI)
database = dbclient[DB_NAME]


user_data = database['users']
force_sub_data = database['force_sub_settings']


async def present_user(user_id: int):
    return bool(user_data.find_one({'_id': user_id}))


async def add_user(user_id: int):
    user_data.insert_one({'_id': user_id})


async def full_userbase():
    return [doc['_id'] for doc in user_data.find()]


async def del_user(user_id: int):
    user_data.delete_one({'_id': user_id})


def _default_force_subscriptions():
    return [
        {'slot': 1, 'channel_id': FORCE_SUB_CHANNEL, 'enabled': FORCE_SUB_CHANNEL_ENABLED},
        {'slot': 2, 'channel_id': FORCE_SUB_CHANNEL2, 'enabled': FORCE_SUB_CHANNEL2_ENABLED},
    ]


async def get_force_subscriptions():
    """Return configured channels and reset a slot when its channel changes."""
    channels = []
    for default in _default_force_subscriptions():
        saved = force_sub_data.find_one({'_id': default['slot']})
        channel_changed = saved is not None and saved.get('channel_id') != default['channel_id']
        if saved is None or channel_changed:
            # A newly configured channel must use its environment on/off setting,
            # not the old channel's saved state or old invite link.
            force_sub_data.update_one(
                {'_id': default['slot']},
                {'$set': {
                    'channel_id': default['channel_id'],
                    'enabled': default['enabled'],
                }, '$unset': {'invite_link': ''}},
                upsert=True,
            )
            enabled = default['enabled']
        else:
            enabled = bool(saved.get('enabled', default['enabled']))
        channels.append({**default, 'enabled': enabled})
    return channels


async def get_or_create_force_subscribe_link(slot: int, create_link):
    """Reuse one request-to-join link for each channel slot."""
    saved = force_sub_data.find_one({'_id': slot}) or {}
    invite_link = saved.get('invite_link')
    if invite_link:
        return invite_link

    invite = await create_link()
    force_sub_data.update_one(
        {'_id': slot},
        {'$set': {'invite_link': invite.invite_link}},
        upsert=True,
    )
    return invite.invite_link


async def toggle_force_subscription(slot: int):
    """Flip one Force Subscribe slot and return its new state."""
    channels = await get_force_subscriptions()
    setting = next((item for item in channels if item['slot'] == slot), None)
    if setting is None:
        raise ValueError('Unknown Force Subscribe slot')

    new_state = not setting['enabled']
    force_sub_data.update_one(
        {'_id': slot},
        {'$set': {'enabled': new_state}},
        upsert=True,
    )
    return new_state
