# import modules
from base import *
from ui.ui_print import *
import releases

name = "torrentio"

default_opts = "https://torrentio.strem.fun/sort=qualitysize|qualityfilter=480p,scr,cam/manifest.json"

session = custom_session()


def get(url):
    try:
        response = session.get(url, timeout=60)
        response = json.loads(
            response.content, object_hook=lambda d: SimpleNamespace(**d))
        return response
    except requests.exceptions.RequestException as e:
        ui_print("[torrentio] error: (request exception): " + str(e), debug=ui_settings.debug)
        return None
    except json.JSONDecodeError as e:
        ui_print("[torrentio] error: (json exception): " + str(e), debug=ui_settings.debug)
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


def _get_imdb_id(query, type):
    try:
        if regex.search(r'(tt[0-9]+)', query, regex.I):
            return regex.search(r'(tt[0-9]+)', query, regex.I).group(), type

        original_type = type
        try:
            if type == "show":
                url = "https://v3-cinemeta.strem.io/catalog/series/top/search=" + query + ".json"
                meta = get(url)
            else:
                url = "https://v3-cinemeta.strem.io/catalog/movie/top/search=" + query + ".json"
                meta = get(url)
            return meta.metas[0].imdb_id, type
        except:
            if original_type == "movie":
                type = "show"
                url = "https://v3-cinemeta.strem.io/catalog/series/top/search=" + query + ".json"
                meta = get(url)
            else:
                type = "movie"
                url = "https://v3-cinemeta.strem.io/catalog/movie/top/search=" + query + ".json"
                meta = get(url)
            return meta.metas[0].imdb_id, type
    except Exception as e:
        ui_print('[torrentio] error: could not find IMDB ID: ' + str(e), debug=ui_settings.debug)
        return None, None

def _get_streams(imdb_id, type, altquery, opts):
    try:
        if type == "show":
            s = (regex.search(r'(?<=S)([0-9]+)', altquery, regex.I).group()
                 if regex.search(r'(?<=S)([0-9]+)', altquery, regex.I) else None)
            e = (regex.search(r'(?<=E)([0-9]+)', altquery, regex.I).group()
                 if regex.search(r'(?<=E)([0-9]+)', altquery, regex.I) else None)
            if s is None or int(s) == 0:
                s = 1
            if e is None or int(e) == 0:
                e = 1
            url = f'https://torrentio.strem.fun/{opts}{"/" if opts else ""}stream/series/{imdb_id}:{s}:{e}.json'
            return get(url)

        url = f'https://torrentio.strem.fun/{opts}{"/" if opts else ""}stream/movie/{imdb_id}.json'
        response = get(url)
        if not hasattr(response, "streams") or not response.streams:
            # If no movie streams found, try searching for it as a show
            s = 1
            e = 1
            url = f'https://torrentio.strem.fun/{opts}{"/" if opts else ""}stream/series/{imdb_id}:{s}:{e}.json'
            return get(url)
        return response
    except Exception as e:
        ui_print('[torrentio] error: could not get streams: ' + str(e), debug=ui_settings.debug)
        return None

def _parse_stream(result):
    try:
        title = result.title.split('\n')[0].replace(' ', '.')
        size_match = regex.search(r'(?<=💾 )([0-9]+.?[0-9]+)(?= GB)', result.title)
        if size_match:
            size = float(size_match.group())
        else:
            size_match = regex.search(r'(?<=💾 )([0-9]+.?[0-9]+)(?= MB)', result.title)
            size = float(size_match.group()) / 1000 if size_match else 0

        links = ['magnet:?xt=urn:btih:' + result.infoHash + '&dn=&tr=']
        seeds_match = regex.search(r'(?<=👤 )([0-9]+)', result.title)
        seeds = int(seeds_match.group()) if seeds_match else 0
        source_match = regex.search(r'(?<=⚙️ )(.*)(?=\n|$)', result.title)
        source = source_match.group() if source_match else "unknown"

        return releases.release(
            '[torrentio: '+source+']', 'torrent', title, [], size, links, seeds)
    except Exception as e:
        ui_print('[torrentio] error: could not parse stream: ' + str(e), debug=ui_settings.debug)
        return None


def scrape(query, altquery):
    from scraper.services import active
    if 'torrentio' not in active:
        return []

    if altquery == "(.*)":
        altquery = query

    type = "show" if regex.search(r'(S[0-9]|complete|S\?[0-9])', altquery, regex.I) else "movie"

    imdb_id, type = _get_imdb_id(query, type)
    if not imdb_id:
        return []

    opts = default_opts.split("/")[-2] if default_opts.endswith("manifest.json") else ""
    response = _get_streams(imdb_id, type, altquery, opts)

    if not hasattr(response, "streams"):
        if response:
            ui_print('[torrentio] error: ' + str(response))
        else:
            ui_print('[torrentio] error: unknown error')
        return []

    if len(response.streams) == 1 and not hasattr(response.streams[0], "infoHash"):
        ui_print('[torrentio] error: "' + response.streams[0].name.replace('\n',
                 ' ') + '" - ' + response.streams[0].title.replace('\n', ' '))
        return []

    scraped_releases = []
    for result in response.streams:
        release = _parse_stream(result)
        if release:
            scraped_releases.append(release)

    return scraped_releases
