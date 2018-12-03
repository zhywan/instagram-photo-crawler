import requests
import json
import time
import random
import os
import bs4
import re
import datetime
import codecs
import winsound


# Configurations
username = ""  # your username
password = ""  # your password
target_id = ""  # the target's username

origin_url = 'https://www.instagram.com'
login_url = origin_url + '/accounts/login/ajax/'
user_agent = 'Chrome/59.0.3071.115'

default_query_id = "50d3631032cf38ebe1a2d758524e3492"  # make it a empty string if you want to find a new query id
default_user_id = ""  # make it a empty string if you do not have a default value
default_end_cursor = ""  # make it a empty string if you do not want to continue from a paused crawl
default_variables = {
    'id': default_user_id,
    'first': 12,
    'after': default_end_cursor
}
# saved URL to continue a paused crawl, with all those required default values
default_target_url = "%s/graphql/query/?query_hash=%s&variables=%s" % (origin_url, default_query_id,
                                                                       json.dumps(default_variables))
if not default_end_cursor:
    default_target_url = ""

avg_time_sleep = 5  # average duration in seconds between two downloads to prevent blocking
n_file_saved = 0  # counting saved files
n_file_discovered = 0  # counting discovered files
old_friend = False  # set it True if you have crawled all medias of this target before to save time
keep_log = True  # set it True if you want to keep the log of output
keep_json_responses = True  # set it True if you want to keep the query responses in json formats (utf-8)
sound_alert = True  # set it True if you want to hear a clip of sound, create a Sounds folder and put wave files in it
if keep_log:
    log_dir_name = 'logs'
    log_info = []  # save the printed messages
if keep_json_responses:
    json_dir_name = 'responses'
    i_response = 0  # number the response
    json_sub_dir = ''

# login ig and get cookies
session = requests.Session()
session.headers = {'user-agent': user_agent}
session.headers.update({'Referer': origin_url})

req = session.get(origin_url)
try:
    req.raise_for_status()
except Exception as exc:
    print('problem occur: %s' % exc)
    exit()

session.headers.update({'X-CSRFToken': req.cookies['csrftoken']})
login_data = {'username': username, 'password': password}
login = session.post(login_url, data=login_data, allow_redirects=True)
try:
    login.raise_for_status()
except Exception as exc:
    print('problem occur: %s' % exc)
    exit()

session.headers.update({'X-CSRFToken': login.cookies['csrftoken']})
cookies = login.cookies
login_text = json.loads(login.text)


def check_args():
    # if required arguments are not embedded, prompt for the user's inputs
    global username
    global password
    global target_id
    if not username or not password or not target_id:
        import getpass
        if not username:
            username = getpass.getpass("ID: ")
        if not password:
            password = getpass.getpass("pw: ")
        if not target_id:
            target_id = getpass.getpass("target ID: ")


def handle_12_posts(data, origin_url, is_first=False):
    """
    # Get url of medias,
    # if the post has single picture, get url,
    # if the post has multiple pictures, get the url of the post,
    # if the post has single video, get the url of the post
    # request the url and get all urls of medias
    # download a media immediately after its discovery
    """
    if is_first:
        edges = data['graphql']['user']['edge_owner_to_timeline_media']['edges']
    else:
        edges = data['data']['user']['edge_owner_to_timeline_media']['edges']
    for i in edges:

        typename = str(i['node']['__typename'])

        if typename == "GraphImage":
            pic_url = str(i['node']['display_url'])
            download_media(typename, pic_url)

        if typename == "GraphVideo":
            code = str(i['node']['shortcode'])
            post_url = origin_url + '/p/' + code + '/?__a=1'
            response = session.get(post_url)
            try:
                response.raise_for_status()
            except Exception as exc:
                print('problem occur: %s' % exc)
                exit()
            post_data = response.json()
            if keep_json_responses:
                log_response(typename, post_data)
            video_url = str(post_data['graphql']['shortcode_media']['video_url'])
            download_media(typename, video_url)

        if typename == "GraphSidecar":
            code = str(i['node']['shortcode'])
            post_url = origin_url + '/p/' + code + '/?__a=1'
            response = session.get(post_url)
            try:
                response.raise_for_status()
            except Exception as exc:
                print('problem occur: %s' % exc)
                exit()

            post_data = response.json()
            if keep_json_responses:
                log_response(typename, post_data)
            node_arr = post_data['graphql']['shortcode_media']['edge_sidecar_to_children']['edges']

            for node in node_arr:
                pic_url = node['node']['display_url']
                download_media(typename, pic_url)


def get_end_cursor(data, is_first=False):
    if is_first:
        end_cursor = data['graphql']['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']
    else:
        end_cursor = data['data']['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']
    return str(end_cursor)


def refresh_url(origin_url, query_id, variables):
    target_url = "%s/graphql/query/?query_hash=%s&variables=%s" % (origin_url, query_id, json.dumps(variables))
    return target_url


def print_info(info):
    print(info)
    if keep_log:
        global log_info
        log_info.append(info)


def download_media(cat, url):
    print_info("[%s] %s" % (cat, url))
    save2file(url)


def save_profile(data):
    profile_url = data['graphql']['user']['profile_pic_url_hd']
    download_media("Profile", profile_url)


def save2file(url):
    global old_friend
    global n_file_saved
    global n_file_discovered
    n_file_discovered += 1
    print_info("%s media got discovered." % n_file_discovered)
    # delay to prevent blocking
    time_sleep = (random.uniform(0, 1) + 1) / 1.5 * avg_time_sleep
    print_info('Sleep for %s seconds.' % time_sleep)
    time.sleep(time_sleep)

    # download one medium
    filename = url.split('?')[0].split('/').pop()
    filepath = target_id + '/' + filename
    if os.path.isfile(filepath) and not os.path.getsize(filepath) == 0:
        print_info('File ' + filename + ' existed.')
        if old_friend:
            print_info('You are old friends.')
            exit()
        return

    with open(filepath, 'wb') as handle:
        response = session.get(url, stream=True)
        try:
            response.raise_for_status()
        except Exception as exc:
            print('problem occur: %s' % exc)
            exit()

        for block in response.iter_content(15000):
            if not block:
                break
            handle.write(block)
        n_file_saved += 1
        print_info("%s file(s) got saved" % n_file_saved)


def get_query_ids(doc):
    query_ids = []
    for script in doc.find_all("script"):
        if script.has_attr("src"):
            text = requests.get("%s%s" % (origin_url, script['src'])).text
            if "queryId" in text:
                for query_id in re.findall("(?<=queryId:\")[0-9A-Za-z]+", text):
                    query_ids.append(query_id)
    print_info('query_ids: ' + str(query_ids))
    return query_ids


def get_user_id(data, is_first):
    if is_first:
        user_id = data['graphql']['user']['id']
    else:
        user_id = data['data']['user']['id']
    return user_id

def get_has_next_page(data, is_first):
    if is_first:
        has_next_page = data['graphql']['user']['edge_owner_to_timeline_media']['page_info']['has_next_page']
    else:
        has_next_page = data['data']['user']['edge_owner_to_timeline_media']['page_info']['has_next_page']
    return has_next_page

def make_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def log_response(cat, data):
    global i_response
    global json_sub_dir
    json_file_path = '%s/response_%s_%s.json' % (json_sub_dir, i_response, cat)
    with open(json_file_path, 'wb') as f:
        json.dump(data, codecs.getwriter('utf-8')(f), ensure_ascii=False)
    i_response += 1


def main():
    global json_sub_dir
    global log_info
    global session
    check_args()
    # create a directory for this target
    make_dir(target_id)
    if keep_log or keep_json_responses:
        time_stamp = datetime.datetime.now().strftime('%Y-%m-%d(%H-%M-%S)')  # help name the log file(s)
    if keep_json_responses:
        json_dir = target_id + '/' + json_dir_name
        make_dir(json_dir)
        json_sub_dir = json_dir + '/responses_' + time_stamp
        make_dir(json_sub_dir)

    if 'default_target_url' not in globals() or not default_target_url:
        target_url = origin_url + '/' + target_id + '/?__a=1'
        is_first = True
    else:
        target_url = default_target_url
        is_first = False
    print_info("Targeted URL is: %s." % target_url)
    req = session.get(target_url)
    try:
        req.raise_for_status()
    except Exception as exc:
        print('problem occur: %s' % exc)
        exit()

    data = req.json()

    # start crawling the target
    if 'default_user_id' not in globals() or not default_user_id:
        user_id = get_user_id(data, is_first)
    else:
        user_id = default_user_id
    print_info('Crawling %s(%s) ...' % (target_id, user_id))
    if is_first:
        if keep_json_responses:
            log_response("Homepage", data)
        save_profile(data)  # save profile picture
        # print out the number of available media
        if len(data['graphql']['user']['edge_owner_to_timeline_media']['edges']) == 0:
            print_info('No available media!')
        else:
            n_media = data['graphql']['user']['edge_owner_to_timeline_media']['count']
            print_info('Number of available resources: ' + str(n_media))
    else:
        if keep_json_responses:
            log_response("Continue", data)

    has_next_page = get_has_next_page(data, is_first)
    if has_next_page:
        print_info("Target still has more than 12 media.")
        if 'default_query_id' not in globals() or not default_query_id:
            end_cursor = get_end_cursor(data, is_first)
            target_url_simple = origin_url + '/' + target_id
            req_simple = session.get(target_url_simple)
            response = bs4.BeautifulSoup(req_simple.text, 'html.parser')
            potential_query_ids = get_query_ids(response)
            success_query = False
            for potential_id in potential_query_ids:
                variables = {
                    'id': user_id,
                    'first': 12,
                    'after': end_cursor
                }
                target_url = refresh_url(origin_url, potential_id, variables)
                req1 = session.get(target_url)
                data1 = req1.json()
                if data1['status'] == 'fail':
                    # empty response, skip
                    continue
                elif 'data' in data1 and\
                        'user' in data1['data'] and\
                        'edge_owner_to_timeline_media' in data1['data']['user'] and\
                        'edges' in data1['data']['user']['edge_owner_to_timeline_media']:
                    is_own_media = True
                    for edge in data1['data']['user']['edge_owner_to_timeline_media']['edges']:
                        if not edge['node']['owner']['id'] == user_id:
                            is_own_media = False
                            break
                    if is_own_media:
                        query_id = potential_id
                        print_info('Correct query id is %s.' % query_id)
                        success_query = True
                        break
            if not success_query:
                print_info("Error extracting Query Id, only latest 12 media can be downloaded.")
        else:
            success_query = True
            query_id = default_query_id
            print_info("Default query id is used: %s." % query_id)
    else:
        print_info("Target has no more than 12 media.")

    # create a log file and save log to file
    if keep_log:
        log_dir = target_id + '/' + log_dir_name
        make_dir(log_dir)
        log_file_path = log_dir + '/log_' + time_stamp + '.txt'
        log_file = open(log_file_path, 'w')
        for info in log_info:
            log_file.write(info + '\n')
        log_info = []

    # Only 12 posts are received when directing to one's profile,
    # we have to get the end_cursor and redirect to get the next 12 posts,
    # keep redirecting until there will be no next page
    while has_next_page and success_query:
        handle_12_posts(data, origin_url, is_first)
        # continue to save log to file
        for info in log_info:
            log_file.write(info + '\n')
        log_info = []

        # fetch the next page
        end_cursor = get_end_cursor(data, is_first)
        if is_first:
            is_first = not is_first
        variables = {
            'id': user_id,
            'first': 12,
            'after': end_cursor
        }
        target_url = refresh_url(origin_url, query_id, variables)
        print_info("New targeted URL is: %s" % target_url)
        try:
            req = session.get(target_url)
            req.raise_for_status()
            data = req.json()
        except Exception as exc:
            print('problem occur: %s' % exc)
            exit()

        if keep_json_responses:
            log_response("Scroll_down", data)
        has_next_page = get_has_next_page(data, is_first)

    # Last posts
    handle_12_posts(data, origin_url, is_first)
    time_stamp2 = datetime.datetime.now().strftime('%Y-%m-%d (%H:%M:%S)')
    print_info('Finished! Saved %s file(s). Discovered %s media. [%s]' % (n_file_saved, n_file_discovered,
                                                                          time_stamp2))

    # continue to save log to file
    for info in log_info:
        log_file.write(info + '\n')
    log_info = []
    log_file.close()

    if sound_alert:
        # ringing a certain number of random sounds
        sounds = os.listdir('Sounds')
        for _ in range(3):
            sound_i = random.randint(0, len(sounds) - 1)
            winsound.PlaySound('Sounds/%s' % sounds[sound_i], winsound.SND_FILENAME)


if __name__ == '__main__':
    main()
