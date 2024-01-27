import argparse
import json
from typing import List, Dict

import requests
from bs4 import BeautifulSoup


GAME_CONFIG = {
    "genshin": {
        "name": "Genshin Impact",
        "bot_name": "Keqing",
        "filename": "genshin-cache.json",
        "avatar": "https://static.wikia.nocookie.net/gensin-impact/images/5/52/Keqing_Icon.png/revision/latest/scale-to-width-down/250",
        "url": "https://genshin-impact.fandom.com/wiki/Promotional_Code",
        "activate": "https://genshin.hoyoverse.com/en/gift?code=",
    },
    "honkai": {
        "name": "Honkai: Star Rail",
        "bot_name": "Huohuo",
        "filename": "honkai-cache.json",
        "avatar": "https://static.wikia.nocookie.net/houkai-star-rail/images/6/68/Character_Huohuo_Icon.png/revision/latest/scale-to-width-down/250",
        "url": "https://honkai-star-rail.fandom.com/wiki/Redemption_Code",
        "activate": "https://hsr.hoyoverse.com/gift?code=",
    }
}


def _parse_duration(duration_html) -> List[str]:
    duration = str(duration_html).split('>')
    for i in range(len(duration)):
        duration[i] = duration[i].replace('<br/', '').replace('\n</td', '').strip()
    return [duration[1], duration[2]]


def _parse_rewards(html_element) -> List[Dict]:
    rewards_list = []

    for item in html_element.select('span.item'):
        name = item.select_one('span.item-text a').text.strip()
        amount = item.select_one('span.item-text').text.replace(name, '').replace(' ×', '').strip()
        image_url = item.select_one('span.hidden > a > img').get('data-src', '') or item.select_one(
            'span.hidden > a > img').get('src', '')

        rewards_list.append({
            'name': name,
            'amount': amount,
            'imageURL': image_url
        })

    return rewards_list


def genshin_impact() -> List[Dict]:
    response = requests.get(GAME_CONFIG['genshin']['url'])
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.select('.wikitable')[0].select('tbody > tr:not(:first-child)')
    output = []

    for index, code_row in enumerate(table):
        code = code_row.contents[1].text.split('[')[0].strip()
        server = code_row.contents[3].text.strip()
        rewards = _parse_rewards(code_row.contents[5])
        duration = _parse_duration(code_row.contents[7])
        is_expired = 'Expired:' in code_row.contents[7].text

        code_item = {
            'code': code,
            'server': server,
            'rewards': rewards,
            'duration': duration,
            'isExpired': is_expired
        }

        if rewards:
            output.append(code_item)

    return output


def honkai_codes() -> List[Dict]:
    response = requests.get(GAME_CONFIG['honkai']['url'])
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.select('.wikitable')[0].select('tbody > tr:not(:first-child)')

    output = []

    for index, code_row in enumerate(table):
        code = code_row.contents[0].text.split('[')[0].strip()
        server = code_row.contents[1].text.strip()
        rewards = _parse_rewards(code_row.contents[2])
        duration = _parse_duration(code_row.contents[3])
        is_expired = 'Expired:' in code_row.contents[3].text

        code_item = {
            'code': code,
            'server': server,
            'rewards': rewards,
            'duration': duration,
            'isExpired': is_expired
        }

        if rewards:
            output.append(code_item)

    return output


def load_codes(game: str) -> List[str]:
    with open(GAME_CONFIG[game]['filename'], "r") as f:
        data = json.load(f)

    return data


def save_codes(game: str, data: List[str]) -> None:
    with open(GAME_CONFIG[game]['filename'], "w") as f:
        json.dump(data, f)


def send_webhook(game: str, data: Dict, webhook: str) -> None:
    rewards_str = ""

    for row in data['rewards']:
        rewards_str += f"{row['name']} ×{row['amount']}\n"

    webhook_data = {
        "content": None,
        "username": GAME_CONFIG[game]['bot_name'],
        "avatar_url": GAME_CONFIG[game]['avatar'],
        "embeds": [
            {
                "title": f"[{data['server']}] {GAME_CONFIG[game]['name']}",
                "description": f"```{data['code']}```\n[Click to activate]({GAME_CONFIG[game]['activate']}{data['code']})\n\n**Valid**\n{'\n'.join(data['duration'])}\n\n**Rewards**\n{rewards_str}"
            }
        ]
    }
    requests.post(webhook, json=webhook_data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("HoYoverse Code Bot")
    parser.add_argument('-g', "--game", choices=['honkai', 'genshin'], help="Specify the game (honkai or genshin)", required=True)
    parser.add_argument("-w", "--webhook", help="Target webhook", required=False)
    args = parser.parse_args()

    if args.game == "genshin":
        codes = genshin_impact()
    else:
        codes = honkai_codes()

    previous_codes = load_codes(args.game)
    new_codes = reversed([x for x in codes if x["code"] not in previous_codes])

    if args.webhook and new_codes:
        for code in new_codes:
            send_webhook(args.game, code, args.webhook)

    save_codes(args.game, [x["code"] for x in codes])
