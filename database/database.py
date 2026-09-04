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
    found = user_data.find_one({'_id': user_id})
    return bool(found)


async def add_user(user_id: int):
    user_data.insert_one({'_id': user_id})


async def full_userbase():
    user_docs = user_data.find()
    return [doc['_id'] for doc in user_docs]


async def del_user(user_id: int):
    user_data.delete_one({'_id': user_id})


def _default_force_subscriptions():
    return [
        {'slot': 1, 'channel_id': FORCE_SUB_CHANNEL, 'enabled': FORCE_SUB_CHANNEL_ENABLED},
        {'slot': 2, 'channel_id': FORCE_SUB_CHANNEL2, 'enabled': FORCE_SUB_CHANNEL2_ENABLED},
    ]


async def get_force_subscriptions():
    """Return both Force Subscribe slots and their persisted on/off state."""
    channels = []
    for default in _default_force_subscriptions():
        saved = force_sub_data.find_one({'_id': default['slot']})
        enabled = default['enabled'] if saved is None else bool(saved.get('enabled'))
        channels.append({**default, 'enabled': enabled})
    return channels


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
