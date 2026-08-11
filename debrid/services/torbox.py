#import modules
from base import *
from ui.ui_print import *
import releases

# (required) Name of the Debrid service
name = "TorBox"
short = "TB"
# (required) Authentification of the Debrid service, can be oauth aswell. Create a setting for the required variables in the ui.settings_list. For an oauth example check the trakt authentification.
# The api key can be provided through the settings.json file (set by the app's settings menu) or through the
# TORBOX_API_KEY environment variable (e.g. when the key is managed outside of the app). The settings.json
# value takes precedence once the app loads its saved settings.
api_key = os.getenv("TORBOX_API_KEY", "") or ""
# Define Variables
session = requests.Session()

def setup(cls, new=False):
    from debrid.services import setup
    setup(cls,new)

# Error Log
def logerror(response):
    if not response.status_code in [200,201,204]:
        ui_print("[torbox] error: (" + str(response.status_code) + ") " + str(response.content), debug=ui_settings.debug)
    if response.status_code == 401:
        ui_print("[torbox] error: (401 unauthorized): torbox api key does not seem to work. check your torbox settings.")

# Get Function
def get(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
        'Authorization': 'Bearer ' + api_key}
    try:
        response = session.get(url, headers=headers)
        logerror(response)
        response = json.loads(response.content, object_hook=lambda d: SimpleNamespace(**d))
    except Exception as e:
        ui_print("[torbox] error: (json exception): " + str(e), debug=ui_settings.debug)
        response = None
    return response

# Post Function
def post(url, data):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
        'Authorization': 'Bearer ' + api_key}
    try:
        response = session.post(url, headers=headers, data=data)
        logerror(response)
        response = json.loads(response.content, object_hook=lambda d: SimpleNamespace(**d))
    except Exception as e:
        ui_print("[torbox] error: (json exception): " + str(e), debug=ui_settings.debug)
        response = None
    return response

# Object classes
class file:
    def __init__(self, id, name, size, wanted_list, unwanted_list):
        self.id = id
        self.name = name
        self.size = size / 1000000000
        self.match = ''
        wanted = False
        unwanted = False
        for key, wanted_pattern in wanted_list:
            if wanted_pattern.search(self.name):
                wanted = True
                self.match = key
                break

        if not wanted:
            for key, unwanted_pattern in unwanted_list:
                if unwanted_pattern.search(self.name) or self.name.endswith('.exe') or self.name.endswith('.txt'):
                    unwanted = True
                    break

        self.wanted = wanted
        self.unwanted = unwanted

    def __eq__(self, other):
        return self.id == other.id

class version:
    def __init__(self, files):
        self.files = files
        self.needed = 0
        self.wanted = 0
        self.unwanted = 0
        self.size = 0
        for file in self.files:
            self.size += file.size
            if file.wanted:
                self.wanted += 1
            if file.unwanted:
                self.unwanted += 1

# (required) Download Function.
def download(element, stream=True, query='', force=False):
    cached = element.Releases
    if query == '':
        query = element.deviation()
    wanted = [query]
    if not isinstance(element, releases.release):
        wanted = element.files()
    for release in cached[:]:
        # if release matches query
        if regex.match(r'(' + query + ')', release.title, regex.I) or force:
            if stream:
                for version in release.files:
                    if hasattr(version, 'files'):
                        if len(version.files) > 0 and version.wanted > len(wanted) / 2 or force:
                            try:
                                response = post('https://api.torbox.app/v1/api/torrents/asynccreatetorrent',
                                                {'magnet': str(release.download[0]), 'seed': '3', 'allow_zip': '0', 'as_queued': '1'})
                                torrent_id = str(response.data.torrent_id)
                            except:
                                ui_print('[torbox] error: could not add magnet for release: ' + release.title, ui_settings.debug)
                                continue
                            release.files = [version]
                            ui_print('[torbox] adding cached release: ' + release.title)
                            return True
                # cached release without a usable file version - add the magnet anyway
                try:
                    response = post('https://api.torbox.app/v1/api/torrents/asynccreatetorrent',
                                    {'magnet': str(release.download[0]), 'seed': '3', 'allow_zip': '0', 'as_queued': '1'})
                    torrent_id = str(response.data.torrent_id)
                    ui_print('[torbox] adding cached release: ' + release.title)
                    return True
                except:
                    ui_print('[torbox] error: could not add magnet for release: ' + release.title, ui_settings.debug)
                    continue
            else:
                try:
                    response = post('https://api.torbox.app/v1/api/torrents/asynccreatetorrent',
                                    {'magnet': str(release.download[0]), 'seed': '3', 'allow_zip': '0', 'as_queued': '1'})
                    torrent_id = str(response.data.torrent_id)
                    ui_print('[torbox] adding uncached release: ' + release.title)
                    return True
                except:
                    ui_print('[torbox] error: could not add magnet for release: ' + release.title, ui_settings.debug)
                    continue
    return False

# (required) Check Function
def check(element, force=False):
    if force:
        wanted = ['.*']
    else:
        wanted = element.files()
    unwanted = releases.sort.unwanted
    wanted_patterns = list(zip(wanted, [regex.compile(r'(' + key + ')', regex.IGNORECASE) for key in wanted]))
    unwanted_patterns = list(zip(unwanted, [regex.compile(r'(' + key + ')', regex.IGNORECASE) for key in unwanted]))

    hashes = []
    for release in element.Releases[:]:
        if len(release.hash) == 40:
            hashes += [release.hash]
        else:
            ui_print("[torbox] error (missing torrent hash): ignoring release '" + release.title + "'", ui_settings.debug)
            element.Releases.remove(release)
    if len(hashes) > 0:
        ui_print("[torbox] checking and sorting all release files ...", ui_settings.debug)
        # the checkcached endpoint only accepts around 100 hashes per request
        for i in range(0, len(hashes), 100):
            batch = hashes[i:i + 100]
            response = get('https://api.torbox.app/v1/api/torrents/checkcached?format=object&list_files=true&hash=' + ','.join(batch))
            if response is None or not hasattr(response, 'data') or response.data is None:
                continue
            for release in element.Releases:
                release_hash = release.hash.lower()
                if hasattr(response.data, release_hash):
                    response_attr = getattr(response.data, release_hash)
                    if getattr(response_attr, 'cached', False):
                        release.cached += ['TB']
                        if hasattr(response_attr, 'files') and response_attr.files is not None:
                            version_files = []
                            for cached_file in response_attr.files:
                                if hasattr(cached_file, 'id') and hasattr(cached_file, 'name') and hasattr(cached_file, 'size'):
                                    version_files += [file(cached_file.id, cached_file.name, cached_file.size, wanted_patterns, unwanted_patterns)]
                            if len(version_files) > 0:
                                release.files += [version(version_files)]
                                # select cached version that has the most wanted, least unwanted files and most files overall
                                release.files.sort(key=lambda x: len(x.files), reverse=True)
                                release.files.sort(key=lambda x: x.wanted, reverse=True)
                                release.files.sort(key=lambda x: x.unwanted, reverse=False)
                                release.wanted = release.files[0].wanted
                                release.unwanted = release.files[0].unwanted
                                release.size = release.files[0].size
        ui_print("done", ui_settings.debug)
