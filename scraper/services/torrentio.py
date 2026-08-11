# import modules
from base import *
from ui.ui_print import *
import releases
import urllib.parse
from torrentio_parser import parse_stream

name = "torrentio"

default_opts = "https://torrentio.strem.fun/sort=qualitysize|qualityfilter=480p,scr,cam/manifest.json"

session = custom_session()


def cinemeta_url(type_, query):
    return "https://v3-cinemeta.strem.io/catalog/" + type_ + "/top/search=" + \
        urllib.parse.quote(query, safe='') + ".json"


def get(url):
    try:
        response = session.get(url, timeout=60)
        response = json.loads(
            response.content, object_hook=lambda d: SimpleNamespace(**d))
        return response
    except:
        return None


def setup(cls, new=False):
    from settings import settings_list
    from scraper.services import active
    settings = []
    for category, allsettings in settings_list:
        for setting in allsettings:
            if setting.cls == cls:
                settings += [setting]
    if settings == []:
        if not cls.name in active:
            active += [cls.name]
    back = False
    if not new:
        while not back:
            print("0) Back")
            indices = []
            for index, setting in enumerate(settings):
                print(str(index + 1) + ') ' + setting.name)
                indices += [str(index + 1)]
            print()
            if settings == []:
                print("Nothing to edit!")
                print()
                time.sleep(3)
                return
            choice = input("Choose an action: ")
            if choice in indices:
                settings[int(choice) - 1].input()
                if not cls.name in active:
                    active += [cls.name]
                back = True
            elif choice == '0':
                back = True
    else:
        if not cls.name in active:
            active += [cls.name]


def scrape(query, altquery):
    from scraper.services import active
    scraped_releases = []
    if not 'torrentio' in active:
        return scraped_releases
    if altquery == "(.*)":
        altquery = query
    type = ("show" if regex.search(
        r'(S[0-9]|complete|S\?[0-9])', altquery, regex.I) else "movie")
    opts = default_opts.split(
        "/")[-2] if default_opts.endswith("manifest.json") else ""
    if type == "show":
        s = (regex.search(r'(?<=S)([0-9]+)', altquery, regex.I).group()
             if regex.search(r'(?<=S)([0-9]+)', altquery, regex.I) else None)
        e = (regex.search(r'(?<=E)([0-9]+)', altquery, regex.I).group()
             if regex.search(r'(?<=E)([0-9]+)', altquery, regex.I) else None)
        if s == None or int(s) == 0:
            s = 1
        if e == None or int(e) == 0:
            e = 1
    plain_text = ""
    if regex.search(r'(tt[0-9]+)', altquery, regex.I):
        query = regex.search(r'(tt[0-9]+)', altquery, regex.I).group()
    else:
        plain_text = copy.deepcopy(query)
        try:
            if type == "show":
                url = cinemeta_url("series", query)
                meta = get(url)
            else:
                url = cinemeta_url("movie", query)
                meta = get(url)
            query = meta.metas[0].imdb_id
        except:
            try:
                if type == "movie":
                    type = "show"
                    s = 1
                    e = 1
                    url = cinemeta_url("series", query)
                    meta = get(url)
                else:
                    type = "movie"
                    url = cinemeta_url("movie", query)
                    meta = get(url)
                query = meta.metas[0].imdb_id
            except:
                ui_print('[torrentio] error: could not find IMDB ID')
                return scraped_releases
    if type == "movie":
        url = 'https://torrentio.strem.fun/' + opts + \
            ("/" if len(opts) > 0 else "") + 'stream/movie/' + query + '.json'
        response = get(url)
        if not hasattr(response, "streams") or len(response.streams) == 0:
            type = "show"
            s = 1
            e = 1
            if plain_text != "":
                try:
                    url = cinemeta_url("series", plain_text)
                    meta = get(url)
                    query = meta.metas[0].imdb_id
                except:
                    ui_print('[torrentio] error: could not find IMDB ID')
                    return scraped_releases
    if type == "show":
        url = 'https://torrentio.strem.fun/' + opts + \
            ("/" if len(opts) > 0 else "") + 'stream/series/' + \
            query + ':' + str(int(s)) + ':' + str(int(e)) + '.json'
        response = get(url)
    if not hasattr(response, "streams"):
        try:
            if not response == None:
                ui_print('[torrentio] error: ' + str(response))
        except:
            ui_print('[torrentio] error: unknown error')
        return scraped_releases
    elif len(response.streams) == 1 and not hasattr(response.streams[0], "infoHash"):
        ui_print('[torrentio] error: "' + response.streams[0].name.replace('\n',
                 ' ') + '" - ' + response.streams[0].title.replace('\n', ' '))
        return scraped_releases
    for result in response.streams:
        parsed = parse_stream(result)
        if parsed is None:
            continue
        scraped_releases += [releases.release(
            '[torrentio: ' + parsed['source'] + ']', 'torrent', parsed['title'], [], parsed['size'], [parsed['link']], parsed['seeds'])]
    return scraped_releases
