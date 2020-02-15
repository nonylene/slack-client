import json
import traceback
import time
import asyncio
from dataclasses import dataclass

import websockets
import websockets.exceptions
import click
import httpx

client = httpx.AsyncClient()


@dataclass
class Config:
    token: str
    default_username: str
    emoji_watch_channel: str
    channel_watch_channel: str
    debug_channel: str


channels = dict()
config: Config = None


async def notify_open():
    message = "Connection opened!"
    print(message)
    # Post slack
    await post_text(config.debug_channel, message)


async def notify_close():
    message = "Connection closed!"
    print(message)
    # post slack
    await post_text(config.debug_channel, message)


async def on_message(message):
    message_data = json.loads(message)
    await asyncio.gather(
        emoji_watch(message_data),
        channel_watch(message_data)
    )


# client features below here
async def emoji_watch(data):
    # https://api.slack.com/events/emoji_changed
    if not "emoji_changed" == data["type"]:
        return

    subtype = data["subtype"]
    if "add" == subtype:
        name = data["name"]
        emoji = f":{name}:"

        # If alias is added, we cannot know url.
        value = data['value']
        aliased = value.startswith('alias:')
        if aliased:
            message = f":raising_hand: Alias added: {emoji} (*{name}*, {value})"
            await post_text(
                config.emoji_watch_channel, message,
                "emoji-bot", emoji,
            )

        else:
            message = f":raising_hand: Added: {emoji} (*{name}*)"

            block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                },
                "accessory": {
                    "type": "image",
                    "image_url": value,
                    "alt_text": emoji,
                }
            }
            data = {
                "text": message,
                "blocks": [block],
            }
            await post_message(
                config.emoji_watch_channel, data,
                "emoji-bot", emoji
            )

    else:
        # Remove
        for name in data["names"]:
            message = f":wave: Removed: :{name}: (*{name}*)"
            await post_text(
                config.emoji_watch_channel, message,
                "emoji-bot", ":upside_down_face:",
            )


async def channel_watch(data):

    def channel_link(channel_id):
        return '<#{0}|{1}>'.format(channel_id, channels[channel_id])

    async def post_channel_message(text):
        await post_text(
            config.channel_watch_channel,
            text,
            'channel-bot',
            ':tokyo_tower:'
        )

    # https://api.slack.com/events/channel_archive
    # https://api.slack.com/events/channel_created
    # https://api.slack.com/events/channel_deleted
    # https://api.slack.com/events/channel_rename
    # https://api.slack.com/events/channel_unarchive
    if data['type'] == 'channel_archive':
        await post_channel_message(
            ':ghost: Archived: {0}'.format(channel_link(data['channel']))
        )

    elif data['type'] == 'channel_created':
        channel_id = data['channel']['id']
        channels[channel_id] = data['channel']['name']
        await post_channel_message(
            ':hatching_chick: Created: {0}'.format(
                channel_link(channel_id)
            )
        )

    elif data['type'] == 'channel_deleted':
        channel_name = channels.pop(data['channel'])
        await post_channel_message(
            ':see_no_evil: Deleted: #{0}'.format(channel_name)
        )

    elif data['type'] == 'channel_rename':
        channel_id = data['channel']['id']
        old_channel_name = channels[channel_id]
        new_channel_name = data['channel']['name']
        channels[channel_id] = new_channel_name
        await post_channel_message(
            f':ocean: Renamed: {channel_link(channel_id)} (#{old_channel_name} :arrow_right: #{new_channel_name})'
        )

    elif data['type'] == 'channel_unarchive':
        await post_channel_message(
            ':sushi: Unarchived: {0}'.format(channel_link(data['channel']))
        )


async def connect():
    token_params = {'token': config.token}
    try:
        # Initial -> get channel list
        r = await client.get('https://slack.com/api/channels.list', params=token_params)
        list_data = r.json()
        global channels
        channels = {c["id"]: c["name"] for c in list_data["channels"]}
    except Exception as e:
        await post_text(
            config.debug_channel,
            "get channel list failed: {0}".format(e),
            ":upside_down_face:"
        )
        raise

    try:
        while True:
            r = await client.get('https://slack.com/api/rtm.connect', params=token_params)
            start_data = r.json()
            websocket_url = start_data["url"]
            try:
                async with websockets.connect(websocket_url) as websocket:
                    await notify_open()
                    async for message in websocket:
                        await on_message(message)
            except websockets.exceptions.ConnectionClosed:
                traceback.print_exc()
                await notify_close()
                print("Reconnecting...")
                # Retry
                time.sleep(2)
                continue
    except Exception as e:
        await post_text(
            config.debug_channel,
            "create websocket failed: {0}".format(e),
            ":upside_down_face:"
        )
        raise


async def post_text(
        channel, text,
        username=None, icon_emoji=":upside_down_face:"
):
    if username is None:
        username = config.default_username
    await post_message(channel, {"text": text}, username, icon_emoji)


async def post_message(
        channel, data_dict,
        username=None, icon_emoji=":upside_down_face:"
):
    if username is None:
        username = config.default_username
    base = {
        "token": config.token,
        "channel": channel,
        "icon_emoji": icon_emoji,
        "username": username
    }
    merged = {**data_dict, **base}
    await client.post("https://slack.com/api/chat.postMessage", data=merged)


@click.command()
@click.option('--token', help='Slack token', type=str, required=True, show_envvar=True)
@click.option('--default-username', help='Default username', type=str, required=True, show_envvar=True)
@click.option('--emoji-watch-channel', help='emoji-watch channel', type=str, required=True,  show_envvar=True)
@click.option('--channel-watch-channel', help='channel-watch channel', type=str, required=True,  show_envvar=True)
@click.option('--debug-channel', help='Debug channel', type=str, required=True,  show_envvar=True)
def main(
    token, default_username, emoji_watch_channel, channel_watch_channel, debug_channel
):
    global config
    config = Config(
        token, default_username, emoji_watch_channel, channel_watch_channel, debug_channel
    )
    asyncio.run(connect())


if __name__ == "__main__":
    main(auto_envvar_prefix='SLACK_CLIENT')
