import re
import traceback
import requests
from bs4 import BeautifulSoup
import json


def fetch_events():
    url = "https://honkai-star-rail.fandom.com/wiki/Events"
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
            imageURL = imageURL.replace("scale-to-width-down/250", "scale-to-width-down/500").strip()
            duration = row.contents[1].text.split(' – ')
            type = row.contents[2].text.split(', ')
            status = statuses[events.index(event)]
            page = 'https://honkai-star-rail.fandom.com' + row.contents[0].select_one('a').get('href', '/wiki/Events').strip()
            
            table = { 'event': name, 'image': imageURL, 'duration': duration, 'type': type, 'status': status, 'page': page}

            all_events[status].append(table)

    return all_events


def fetch_codes():
    url = "https://honkai-star-rail.fandom.com/wiki/Redemption_Code"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.select('.wikitable')[0].select('tbody > tr:not(:first-child)')

    codes = {'expiredCodes': [], 'activeCodes': []}
    for code_row in table:
        code = code_row.contents[0].text.split('[')[0].strip()
        server = code_row.contents[1].text.strip()
        rewards = parse_rewards(code_row.contents[2])
        duration = parse_duration(code_row.contents[3].text)
        is_expired = 'Expired:' in code_row.contents[3].text

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
        name = item.select_one('span.item-text a').text
        amount = int(item.select_one('span.item-text').text.replace(name, '').replace(' ×', '').strip())
        image_url = item.select_one('span.hidden > a > img').get('data-src', '') or item.select_one('span.hidden > a > img').get('src', '')

        rewards_list.append({
            'name': name,
            'amount': amount,
            'imageURL': image_url
        })

    return rewards_list


def parse_duration(duration):
    match = re.search(r'Discovered: (.+?)(?:Valid until|Expired|Valid)?: (.+)', duration)
    if match:
        discovered = match.group(1).strip()
        valid_until = match.group(2).strip()
        return [discovered, valid_until]


def save_to_json(events, codes):
    data = {
        'Events': events,
        'Codes': codes
    }

    with open("star-rail-data.json", "w") as json_file:
        json.dump(data, json_file)


if __name__ == "__main__":
    try:
        events = fetch_events()
        codes = fetch_codes()
        save_to_json(events, codes)
    except Exception as e:
        print(e)
        traceback.print_exc()
        SystemExit(e)
