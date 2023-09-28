import re
import traceback
import requests
from bs4 import BeautifulSoup
import json

def fetch_events():
    url = "https://genshin-impact.fandom.com/wiki/Event"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    events = [soup.select('.wikitable')[i].select('tbody > tr:not(:first-child)') for i in range(3)]
    statuses = ['Current', 'Upcoming', 'Permanent']
    all_events = {'Current': [], 'Upcoming': [], 'Permanent': []}

    for event in events:
        for row in event:
            name = row.contents[0].text.strip()
            imageURL = row.select_one('img').get('data-src', '') or row.select_one('img').get('src', '').strip()
            duration = row.contents[1].text.split(' – ')
            type = row.contents[2].text.split(', ')
            status = statuses[events.index(event)]
            page = 'https://genshin-impact.fandom.com' + row.contents[0].select_one('a').get('href', '/wiki/Event').strip()
            
            table = { 'event': name, 'image': imageURL, 'duration': duration, 'type': type, 'status': status, 'page': page}

            all_events[status].append(table)

    return all_events


def fetch_codes():
    url = "https://genshin-impact.fandom.com/wiki/Promotional_Code"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    # with open("genshin_impact_promo_codes.html", "w", encoding="utf-8") as file: file.write(response.text)
    # with open("genshin_impact_promo_codes.html", "r", encoding="utf-8") as file: html_content = file.read()
    # soup = BeautifulSoup(html_content, 'html.parser')

    table = soup.select('.wikitable')[0].select('tbody > tr:not(:first-child)')

    codes = {'activeCodes': [], 'expiredCodes': []}
    for code_row in table:
        code = code_row.contents[1].text.split('[')[0].strip()
        server = code_row.contents[3].text.strip()
        rewards = parse_rewards(code_row.contents[5])
        duration = parse_duration(code_row.contents[7])
        is_expired = 'Expired:' in code_row.contents[7].text

        code_item = {
            'code': code,
            'server': server,
            'rewards': rewards,
            'duration': duration,
            'isExpired': is_expired
        }

        if rewards == []:
            pass
        elif is_expired:
            codes['expiredCodes'].append(code_item)
        else:
            codes['activeCodes'].append(code_item)

    return codes

def parse_rewards(html_element):
    rewards_list = []

    for item in html_element.select('span.item'):
        name = item.select_one('span.item-text a').text.strip()
        amount = item.select_one('span.item-text').text.replace(name, '').replace(' ×', '').strip()
        image_url = item.select_one('span.hidden > a > img').get('data-src', '') or item.select_one('span.hidden > a > img').get('src', '')

        rewards_list.append({
            'name': name,
            'amount': amount,
            'imageURL': image_url
        })

    return rewards_list
def parse_duration(duration_html):
    duration = str(duration_html).split('>')
    for i in range(len(duration)): 
        duration[i] = duration[i].replace('<br/', '').replace('\n</td', '').strip()
    return [duration[1], duration[2]]


def save_to_json(events, codes):
    data = {
        'Events': events,
        'Codes': codes
    }

    with open("genshin-impact-data.json", "w") as json_file:
        json.dump(data, json_file, indent=4)

def discord_notify(content, error=False):
    discord_id = "1022735992014254183"
    discord_webhook = "https://ptb.discord.com/api/webhooks/1031955469998243962/UO379MCHeXTXwk9s86qeZedKKNOa5aDVMHInqGea_dUEOzfPZf66i00CPbGOA0lOkIxp"
    
    if error:
        content = f"<@{discord_id}> {content}\nCheck https://github.com/jeryjs/data-scraper-for-star-rail-helper/actions/workflows/actions.yml for more details."

    payload = {
        'username': 'HoYo Scraper',
        'avatar_url': 'https://i.imgur.com/8elFANR.jpg',
        'content': content,
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(discord_webhook, json=payload, headers=headers)
    
    if response.status_code == 204:
        print("Successfully notified via Discord.")
    else:
        print(f"Failed to notify via Discord. Status code: {response.status_code}")


if __name__ == "__main__":
    try:
        events = fetch_events()
        codes = fetch_codes()
        save_to_json(events, codes)
        discord_notify("`genshin-impact-data.json` was updated.")
    except Exception as e:
        discord_notify("Whoops~ Looks like HoYo Scraper ran into an error.", True)
        print(e)
        traceback.print_exc()
        SystemExit(e)
