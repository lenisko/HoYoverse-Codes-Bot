import sys
import argparse
import json
from typing import List, Dict

import requests
from bs4 import BeautifulSoup

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
)

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
    },
}


def _parse_duration(td) -> Dict[str, str]:
    text = td.get_text(separator=" ", strip=True)
    discovered = None
    valid_until = None

    if "Discovered:" in text:
        parts = text.split("Discovered:")
        discovered_part = parts[1].split("Valid")[0].strip()
        discovered = discovered_part

    if "Valid until:" in text:
        valid_until = text.split("Valid until:")[-1].strip()
    elif "Valid:" in text:
        valid_until = text.split("Valid:")[-1].strip()

    return {
        "discovered": discovered,
        "validUntil": valid_until
        if valid_until and valid_until.lower() != "(indefinite)"
        else None,
    }


def _parse_rewards(html_element) -> List[Dict]:
    rewards_list = []

    for item in html_element.select("span.item"):
        name_tag = item.select_one("span.item-text a")
        name = name_tag.text.strip() if name_tag else ""

        item_text = item.select_one("span.item-text")
        amount = (
            item_text.text.replace(name, "").replace(" ×", "").strip()
            if item_text
            else ""
        )

        img_tag = item.select_one("span.hidden img")
        image_url = img_tag.get("data-src") or img_tag.get("src") if img_tag else ""

        if name:
            rewards_list.append({"name": name, "amount": amount, "imageURL": image_url})

    return rewards_list


def genshin_impact() -> List[Dict]:
    response = SESSION.get(GAME_CONFIG["genshin"]["url"])
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("tbody > tr")
    output = []

    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 5:
            continue

        code_link = tds[1].find("a", href=True)
        if not code_link:
            continue

        code = code_link.text.strip()
        server = tds[2].text.strip()
        rewards = _parse_rewards(tds[3])
        duration = _parse_duration(tds[4])
        is_expired = False

        code_item = {
            "code": code,
            "server": server,
            "rewards": rewards,
            "duration": duration,
            "isExpired": is_expired,
        }

        if rewards:
            output.append(code_item)

    return output


def honkai_codes() -> List[Dict]:
    response = SESSION.get(GAME_CONFIG["honkai"]["url"])
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    table_rows = soup.select_one(".wikitable").select("tbody > tr:not(:first-child)")

    output = []

    for row in table_rows:
        tds = row.find_all("td")
        if len(tds) < 4:
            continue

        code_tag = tds[0].find("code")
        if code_tag:
            code = code_tag.text.strip()
        else:
            code = tds[0].get_text(strip=True).split("[")[0].replace("Quick Redeem", "").strip()
        if not code:
            continue
        server = tds[1].text.strip()
        rewards = _parse_rewards(tds[2])
        duration = _parse_duration(tds[3])
        is_expired = "Expired:" in tds[3].text

        if not rewards:
            continue

        code_item = {
            "code": code,
            "server": server,
            "rewards": rewards,
            "duration": duration,
            "isExpired": is_expired,
        }

        output.append(code_item)

    return output


def load_codes(game: str) -> List[str]:
    with open(GAME_CONFIG[game]["filename"], "r") as f:
        data = json.load(f)

    return data


def save_codes(game: str, data: List[str]) -> None:
    with open(GAME_CONFIG[game]["filename"], "w") as f:
        json.dump(data, f)


def send_webhook(game: str, data: Dict, webhook: str) -> None:
    rewards_text = ""
    for reward in data["rewards"]:
        rewards_text += f"×{reward['amount']} {reward['name']}\n"

    fields = [
        {
            "name": "Discovered",
            "value": data["duration"].get("discovered") or "Unknown",
            "inline": False,
        },
        {
            "name": "Valid Until",
            "value": data["duration"].get("validUntil") or "Indefinite",
            "inline": False,
        },
    ]

    embed = {
        "title": f"[{data['server']}] {GAME_CONFIG[game]['name']}",
        "url": f"{GAME_CONFIG[game]['activate']}{data['code']}",
        "description": f"**Code:** `{data['code']}`\n\n**Rewards**\n{rewards_text.strip()}",
        "color": 0x00BFFF,
        "fields": fields,
        "footer": {"text": f"{GAME_CONFIG[game]['name']} • {data['code']}"},
    }

    webhook_data = {
        "content": None,
        "username": GAME_CONFIG[game]["bot_name"],
        "avatar_url": GAME_CONFIG[game]["avatar"],
        "embeds": [embed],
    }

    SESSION.post(webhook, json=webhook_data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("HoYoverse Code Bot")
    parser.add_argument(
        "-g",
        "--game",
        choices=["honkai", "genshin"],
        help="Specify the game (honkai or genshin)",
        required=True,
    )
    parser.add_argument("-w", "--webhook", help="Target webhook", required=False)
    parser.add_argument("-t", "--test", help="Test", action="store_true")
    args = parser.parse_args()

    if args.game == "genshin":
        codes = genshin_impact()
    else:
        codes = honkai_codes()

    if args.test:
        from pprint import pprint

        pprint(codes)
        sys.exit(0)

    previous_codes = load_codes(args.game)
    new_codes = reversed([x for x in codes if x["code"] not in previous_codes])

    if args.webhook and new_codes:
        for code in new_codes:
            send_webhook(args.game, code, args.webhook)

    save_codes(args.game, [x["code"] for x in codes])
