# slack-client

My super useful slack client.

[Docker Hub (master branch only)](https://hub.docker.com/r/nonylene/slack-client)

## Requirements

- pipenv
- Python 3

## Setup

```sh
$ poetry install
```

## Usage

```sh
$ poetry run python3 slack-client.py --help
Usage: slack-client.py [OPTIONS]

Options:
  --token TEXT                  Slack token  [env var: SLACK_CLIENT_TOKEN;
                                required]
  --default-username TEXT       Default username  [env var:
                                SLACK_CLIENT_DEFAULT_USERNAME; required]
  --emoji-watch-channel TEXT    emoji-watch channel  [env var:
                                SLACK_CLIENT_EMOJI_WATCH_CHANNEL; required]
  --channel-watch-channel TEXT  channel-watch channel  [env var:
                                SLACK_CLIENT_CHANNEL_WATCH_CHANNEL; required]
  --debug-channel TEXT          Debug channel  [env var:
                                SLACK_CLIENT_DEBUG_CHANNEL; required]
  --help                        Show this message and exit.
```

## License and Notices

See [LICENSE.md](./LICENSE.md) for slack-client and [DOCKER_NOTICE](https://github.com/nonylene/slack-client/blob/master/DOCKER_NOTICE) for Docker image notices.
