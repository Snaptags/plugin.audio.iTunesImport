import xbmcvfs
import xbmcgui
import plistlib
import json
import datetime
import re
import time
import pytz

class PlistEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, plistlib.Data):
      return "*data*"
    if isinstance(obj, datetime.datetime):
      return obj.strftime("%c")
    return super(PlistEncoder, self).default(obj)

class ITunesParser(object):
  DOWNLOAD_PROGRESS = 50

  def __init__(self, library_xml_uri, addonname='iTunes Import'):
    self.library_xml_uri = library_xml_uri
    self.addonname = addonname
    self.cached_library_xml_path = "special://temp/itunes_import-cache-music_library.xml"
    self.cached_library_path = "special://temp/itunes_import-cache-library.json"
    self.cached_playlists_path = "special://temp/itunes_import-cache-playlists.json"
    self._playlists = None
    self._plist = None
    self.progressDialog = None

  @property
  def plist(self):
    if not self._plist:
      self.parse_library_xml()
      self.finish_progress()
    return self._plist

  @property  
  def playlists(self):
    if not self._playlists:
      self.parse_library_xml(abort_unless_needed=True)
      if not self._playlists:
        self.load_playlist_index()
      self.finish_progress()
    return self._playlists

  def start_progress(self):
    if not self.progressDialog:
      self.progressDialog = xbmcgui.DialogProgress()
      self.progressDialog.create(self.addonname, 'Downloading Plist')
      self.progressDialog.update(1)

  def finish_progress(self):
    if self.progressDialog:
      self.progressDialog.update(100)
      self.progressDialog.close()
      self.progressDialog = None

  def download_file_to_cache(self, last_time=None):
    cache_file = None

    f = xbmcvfs.File(self.library_xml_uri, 'r')
    chunk_size = 4096
    bytes_read = 0
    file_size = f.size()
    while bytes_read < file_size:
      chunk = f.read(chunk_size)
      if not chunk:
        break;

      # scan the first chunk before writing the file to see if the file is updated since last time
      if not cache_file: 
        if last_time:
          matches = re.search(r'<key>Date</key><date>([^<]+)</date>', chunk, re.IGNORECASE)
          if matches:
            t = matches.group(1)
            print ("t: {0}".format(t))

            chunk_time = pytz.utc.localize(datetime.datetime(*(time.strptime(t, "%Y-%m-%dT%H:%M:%SZ"))[0:6]))
            print("chunk:{0}  last:{1}".format(chunk_time, last_time))
            if chunk_time < last_time:
              # file hasnt changed since last time we ran
              return False
        cache_file = xbmcvfs.File(self.cached_library_xml_path, 'w')

      cache_file.write(chunk)
      bytes_read += len(chunk)
      self.progressDialog.update(int(bytes_read/float(file_size)*self.DOWNLOAD_PROGRESS))
    f.close()
    cache_file.close()
    return True

  def parse_library_xml(self, abort_unless_needed=False):
    self.start_progress()

    last_time = None
    if xbmcvfs.exists(self.cached_library_xml_path):
      local_last_time = datetime.datetime.fromtimestamp(xbmcvfs.Stat(self.cached_library_xml_path).st_ctime())

      local_zone = pytz.timezone('US/Pacific')
      last_time = local_zone.localize(local_last_time)
      print "local: {0}".format(local_last_time)

    if self.download_file_to_cache(last_time):
      # new file was downloaded, update our library cache
      self.progressDialog.update(self.DOWNLOAD_PROGRESS, "Parsing: iTunes Music Library.xml")
      cache_file = xbmcvfs.File(self.cached_library_xml_path, 'r')
      self._plist = plistlib.readPlist(cache_file)
      cache_file.close()

      self.progressDialog.update(55, "Build: library index")
      self.build_playlist_index(self._plist)

      self.progressDialog.update(60, "Dump: library index")
      json_file = xbmcvfs.File(self.cached_library_path, 'w')
      json.dump(self._plist, json_file, cls=PlistEncoder)
      json_file.close()
    elif not abort_unless_needed:
      self.progressDialog.update(60, "Loading cached iTunes Music Library.xml")
      json_file = xbmcvfs.File(self.cached_library_path, 'r')
      self._plist = json.load(json_file)
      json_file.close()

  def build_playlist_index(self, plist):
    playlists = {}
    for playlist in plist['Playlists']:
      if not playlist.get('Distinguished Kind', None) and not playlist.get('Master', False): # skip internal 
        playlistId = int(playlist['Playlist ID'])
        playlists[playlistId] = {
          'Playlist ID': playlistId,
          'Name': playlist['Name'], 
          'Tracks': [plist['Tracks'][str(item['Track ID'])] for item in playlist.get('Playlist Items', [])],
        }
    self._playlists = playlists
    self.dump_playlist_index()
    return playlists

  def dump_playlist_index(self):
    playlist_cache_file = xbmcvfs.File(self.cached_playlists_path, 'w')
    json.dump(self._playlists, playlist_cache_file, cls=PlistEncoder)
    playlist_cache_file.close()

  def load_playlist_index(self):
    if xbmcvfs.exists(self.cached_playlists_path):
      self.progressDialog.update(75, "Loading playlist cache")
      print("playlist cache exists, loading it")
      playlist_cache_file = xbmcvfs.File(self.cached_playlists_path, 'r')
      self._playlists = json.load(playlist_cache_file)
      playlist_cache_file.close()
      return True
    print("playlist cache miss")
    return False
