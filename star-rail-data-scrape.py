import re
import traceback
import requests
from bs4 import BeautifulSoup
import json

discord_message = ""

def fetch_events():
    print('FETCHING EVENTS FOR STAR RAIL...')
    url = "https://honkai-star-rail.fandom.com/wiki/Events"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    events = [soup.select('.wikitable')[i].select('tbody > tr:not(:first-child)') for i in range(3)]
    statuses = ['Current', 'Upcoming', 'Permanent']
    all_events = {'Current': [], 'Upcoming': [], 'Permanent': []}

    for i, event in enumerate(events):
        print(f'Getting {statuses[i]} events...')
        for index, row in enumerate(event):
            try:
                print(f'[{index}] getting event:', end=' ')
                name = row.contents[0].text.strip()
                print(name)
                imageURL = row.select_one('img').get('data-src', '') or row.select_one('img').get('src', '')
                duration = row.contents[1].text.split(' – ')
                type = row.contents[2].text.split(', ')
                status = statuses[events.index(event)]
                page = 'https://honkai-star-rail.fandom.com' + row.contents[0].select_one('a').get('href', '/wiki/Events').strip()
                
                table = { 'event': name, 'image': imageURL, 'duration': duration, 'type': type, 'status': status, 'page': page}

                all_events[status].append(table)
            except Exception as e:
                print("Error: " + str(e.args[0]))
                global discord_message
                error_count = discord_message.count('\n')+1
                discord_message += f"> `[{error_count}] Error: {str(e.args[0])}`\n"

    return all_events


def fetch_codes():
    print('FETCHING CODES FOR STAR RAIL...')
    url = "https://honkai-star-rail.fandom.com/wiki/Redemption_Code"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    # with open("star_rail_promo_codes.html", "w", encoding="utf-8") as file: file.write(response.text)
    # with open("star_rail_promo_codes.html", "r", encoding="utf-8") as file: html_content = file.read()
    # soup = BeautifulSoup(html_content, 'html.parser')

    table = soup.select('.wikitable')[0].select('tbody > tr:not(:first-child)')

    codes = {'activeCodes': [], 'expiredCodes': []}
    for index, code_row in enumerate(table):
        try:
            print(f'[{index}] getting code:', end=' ')
            code = code_row.contents[0].text.split('[')[0].strip()
            print(code)
            server = code_row.contents[1].text.strip()
            rewards = parse_rewards(code_row.contents[2])
            duration = parse_duration(code_row.contents[3])
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
        except Exception as e:
            print("Error: " + str(e.args[0]))
            global discord_message
            error_count = discord_message.count('\n')+1
            discord_message += f"> `[{error_count}] Error: {str(e.args[0])}`\n"

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

    with open("star-rail-data.json", "w") as json_file:
        json.dump(data, json_file, indent=4)

def discord_notify(content, error=False):
    discord_id = "1022735992014254183"
    discord_webhook = "https://ptb.discord.com/api/webhooks/1031955469998243962/UO379MCHeXTXwk9s86qeZedKKNOa5aDVMHInqGea_dUEOzfPZf66i00CPbGOA0lOkIxp"
    
    if error:
        content =   f"<@{discord_id}> {content}" \
                    f"Check https://github.com/jeryjs/data-scraper-for-star-rail-helper/actions/workflows/actions.yml for more details."

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


def run_with_error_handling(func):
    try:
        return func()
    except Exception as e:
        print("Error: " + str(e.args[0]))
        traceback.print_exc()
        global discord_message
        error_count = discord_message.count('\n')+1
        discord_message += f"> `[{error_count}] Error: {str(e.args[0])}`\n"
        discord_notify(f"Whoops~ Looks like HoYo Scraper ran into the following errors:\n{discord_message}", True)

if __name__ == "__main__":
    events = run_with_error_handling(fetch_events)
    codes = run_with_error_handling(fetch_codes)
    save_to_json(events, codes)

    discord_notify(f"HoYo Scraper operation completed.\n{discord_message}")
