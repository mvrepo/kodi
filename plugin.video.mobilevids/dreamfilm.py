# -*- coding: utf-8 -*-
import urllib
import urllib2
import re
import json
from codecs import BOM_UTF8
import logging
import xbmcaddon

import resolvers
from models import Item, Episode, Season

addon       = xbmcaddon.Addon()
user = addon.getSetting('user')
passw = addon.getSetting('pass')
API_BASE_URL = 'https://mobilevids.org/kodiapi/search.php?'+ ('user=%s&pass=%s&' % (user, passw))
ITEMS_PER_PAGE = 25

GENRES = ["Action", "Anime", "Animation", "Adventure", "Biography", "Documentary", "Drama", "Family", "Fantasy", "Christmas", "Comedy", "War", "History", "Crime", "Music", "Musical", "Mystery", "Reality", "Romance", "Sci-Fi", "Horror", "Sport", "Swedish", "Thriller", "Western"]

def _api_url(type='list', page=0, q=None,
              serie=None, id=None, hd=False, genres=None, sort=None, climb=None):
    params = []
    params.append(('type','list'))
    params.append(('offset', page * ITEMS_PER_PAGE))
    params.append(('limit', 25))
    if q:
        params.append(('q', urllib.quote(q)))
    if serie:
        params.append(('p', serie))
    if hd:
        params.append(('hd', '1'))
    if sort:
        params.append(('sort', sort))
    if climb:
        params.append(('climb', climb))
    if genres:
        params.append(('genres', genres))
    if id:
        params.append(('id', id))
    return API_BASE_URL +  "&".join(("%s=%s" % (str(a), str(b)) for a,b in params))

def _paged_api_url(**kwargs):
    def wrapped(page):
        return _api_url(page=page, **kwargs)
    return wrapped

POPULAR_MOVIES_LISTING = 1
POPULAR_SERIES_LISTING = 2
LATEST_UPLOADED_LISTING = 3
BROWSE_MOVIES_LISTING = 4
BROWSE_SERIES_LISTING = 5
HD_ONLY_LISTING = 6

LISTING_NAMES = [

    (BROWSE_SERIES_LISTING, "Latest episodes"),
    (BROWSE_MOVIES_LISTING, "Latest movies"),

]

PAGED_LISTING_URLS = {
    BROWSE_MOVIES_LISTING: _paged_api_url(type='list', serie='recent_movies', sort='alpha', climb='1'),
    BROWSE_SERIES_LISTING: _paged_api_url(type='list', serie='recent_tv', sort='alpha', climb='1'),
    LATEST_UPLOADED_LISTING: _paged_api_url(type='list', sort='time', climb='0'),
}

def listing(listing_type, page=0):
    url = PAGED_LISTING_URLS[listing_type](page)
    api_response = _api_request(url)
    return _apiresponse_to_items(api_response)


def search(q, letters, page=0):
    url = _search_url(urllib.quote(q), letters, 0)
    api_response = _api_request(url)
    return _apiresponse_to_items(api_response)

def list_seasons(serie_id):
    url = API_BASE_URL + ('p=tv&type=episodes&id=%s' % serie_id)
    api_response  = _api_request(url)
    return _apiresponse_to_items(api_response)

def list_genre(genre, serie, page):
    url = _api_url(genres=genre, page=page, serie=serie, sort='alpha', climb='1')
    api_response  = _api_request(url)
    return _apiresponse_to_items(api_response)


def streams_from_player_url(url):
    if 'mail.ru' in url:
        return resolvers.mailru_streams(url)
    if 'picasaweb.google.com' in url:
        return resolvers.picasa_streams(url)
    if 'ok.ru' in url:
        return resolvers.okru_streams(url)
    if 'vkpass.com' in url:
        return resolvers.vkpass_streams(url)

    html = _fetch_html(url)
    if 'vk.com' in url:
        return resolvers.vk_streams(html)
    if 'docs.google.com' in url:
        return resolvers.google_streams(html)
    if 'dreamfilm.se' in url:
        return resolvers.leanback_streams(html)
    return [('video', url)]


def subtitles_from_url(url):
    subs = re.findall('&c\d+_file=\s*(?P<url>.*?)\s*[&$]', url)

    for idx, s in enumerate(subs):
        if '://' not in s:
            # No protocol given, assume http
            subs[idx] = 'http://' + s

    return subs


def _search_url(q, letters, page=0):
    offset = page * ITEMS_PER_PAGE
    return API_BASE_URL + ('p=search&q=%s&type=list&offset=%d&limit=%d&letters=%s' % (q, offset, ITEMS_PER_PAGE,letters))


def _series_to_list(json_data, serie_id):
    response = json.loads(_strip_bom(json_data))
    items = []
    for entry in response['data']:
        item = Item(entry['id'], entry['title'],
                    entry['genres'], entry.get('url', None),
                    entry['type'] == "1", entry['poster'])
        items.append(item)
    return items


def _make_season(serie_id, episodes):
    return Season(serie_id, episodes[0].season, sorted(episodes, key=lambda x: natural_sort_key(x.episode)))

def _api_request(url):
    logging.warning("URL: " + url);
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    response = opener.open(url)
    return response.read()

def _apiresponse_to_items(json_data):
    response = json.loads(_strip_bom(json_data))
    items = []
    for entry in response['data']:
        item = Item(entry['id'], entry['title'],
                    entry['genres'], entry.get('url', None),
                    entry['type'] == "2", entry['poster'])
        items.append(item)
    return items

def _strip_bom(string, bom=BOM_UTF8):
    if string.startswith(bom):
        return string[len(bom):]
    else:
        return string

def _fetch_html(url):
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0 (iPhone; CPU iPhone OS 7_0 like Mac OS X; en-us) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53')]
    response = opener.open(url)
    return response.read()

    response = urllib2.urlopen(url)
    html = response.read()
    return html

def _head_request(url):
    request = urllib2.Request(url)
    request.get_method = lambda : 'HEAD'

    response = urllib2.urlopen(request)
    print response.info()

def natural_sort_key(s, _nsre=re.compile('([0-9]+)')):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(_nsre, s)]

if __name__ == '__main__':
    print search('abba');
