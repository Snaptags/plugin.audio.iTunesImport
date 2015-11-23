import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmc
import xbmcvfs
import urllib
import urlparse
import plistlib
import StringIO
import sys
import json
import random
import os

__base__ = sys.argv[0]
__handle__ = int(sys.argv[1])
__args__ = urlparse.parse_qs(sys.argv[2][1:])


__addon__ = xbmcaddon.Addon(id="plugin.audio.iTunesImport")
__addonname__ = __addon__.getAddonInfo('name')
__addonid__ = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')

music_playlists_path = xbmc.translatePath("special://profile/playlists/music")

library_xml_path = __addon__.getSetting("library_xml_path")
if not library_xml_path:
  __addon__.openSettings()
  library_xml_path = __addon__.getSetting("library_xml_path")


screen = __args__.get('screen', ['top'])[0]
print "base:{base} handle:{handle} args:{args} screen:{screen}".format(base=__base__, handle=__handle__, args=__args__, screen=screen)

def build_url(query):
    return "{base}?{query}".format(base=__base__, query=urllib.urlencode(query))

def parse_library_xml():
  progress = xbmcgui.DialogProgress()
  progress.create(__addonname__, 'Downloading Plist')
  progress.update(1)

  f = xbmcvfs.File(library_xml_path, 'r')
  buffer = StringIO.StringIO()
  chunk_size = 4096
  bytes_read = 0
  file_size = f.size()
  while bytes_read < file_size:
    chunk = f.read(chunk_size)
    if not chunk:
      break;
    buffer.write(chunk)
    bytes_read += len(chunk)
    progress.update(int(bytes_read/float(file_size)*90))

  buffer.seek(0,0)
  progress.update(90, "Parsing Plist")

  plist = plistlib.readPlist(buffer)
  progress.close()
  return plist


def json_rpc(method, request_id=None, **kwargs):
  if request_id is None:
    request_id = random.randint(0, sys.maxint)
  payload = {"jsonrpc": "2.0", "method": method, "params": kwargs, "id": request_id}
  return json.loads(xbmc.executeJSONRPC(json.dumps(payload)))


_album_index = {}
_artist_index = {}
def find_song(title='', artist='', album=''):
  # print "find:  title={0} artist={1} album={2}".format(title, artist, album)
  song = None
  if album:
    if album not in _album_index:
      response = json_rpc("AudioLibrary.GetSongs", properties=['title','artist','album','file','rating'], filter={'album': album})
      if 'songs' in response['result']:
        a = {}
        for song in response['result']['songs']:
          a[song['title']] = song
        _album_index[album] = a
      else:
        # print "not found:  title={0} artist={1} album={2}".format(title, artist, album)
        return
    song = _album_index[album].get(title, None)
  elif artist:
    if artist not in _artist_index:
      response = json_rpc("AudioLibrary.GetSongs", properties=['title','artist','album','file','rating'], filter={'artist': artist})
      if 'songs' in response['result']:
        a = {}
        for song in response['result']['songs']:
          a[song['title']] = song
        _artist_index[artist] = a
      else:
        # print "not found:  title={0} artist={1} album={2}".format(title, artist, album)
        return
    song = _artist_index[artist].get(title, None)
  # if song is None:
    # print "Could not find title={0} artist={1} album={2}".format(title, artist, album)
  return song




if screen == 'top':
  # Import Playlist
  playlists_url = build_url({'screen': 'playlists'})
  import_playlist_item = xbmcgui.ListItem('Import Playlist', iconImage='DefaultFolder.png')
  xbmcplugin.addDirectoryItem(handle=__handle__, url=playlists_url, listitem=import_playlist_item, isFolder=True)

  # Import Ratings 
  ratings_url = build_url({'screen': 'import-ratings'})
  ratings_item = xbmcgui.ListItem('Import Ratings', iconImage='DefaultFile.png')
  xbmcplugin.addDirectoryItem(handle=__handle__, url=ratings_url, listitem=ratings_item, isFolder=False)
  xbmcplugin.endOfDirectory(handle=__handle__, succeeded=True)

elif screen == 'playlists':
  library = parse_library_xml()
  for playlist in library.get('Playlists', []):
    if not playlist.get('Distinguished Kind', None) and not playlist.get('Master', False): # skip internal 
      url = build_url({'screen': 'import-playlist', 'playlistId': playlist['Playlist ID']})
      li = xbmcgui.ListItem(playlist['Name'])
      xbmcplugin.addDirectoryItem(handle=__handle__, url=url, listitem=li)
  xbmcplugin.endOfDirectory(handle=__handle__, succeeded=True)

elif screen == 'import-playlist':
  playlistId = int(__args__.get('playlistId')[0])
  library = parse_library_xml()
  playlist = next(p for p in library['Playlists'] if p['Playlist ID'] == playlistId)
  new_path = os.path.join(music_playlists_path, "{name}.pls".format(name=playlist['Name']))
  with open(new_path, 'w') as new_playlist:
    new_playlist.write("[playlist]\n")
    i = 1

    for item in playlist['Playlist Items']:
      track = library['Tracks'][str(item['Track ID'])]
      song = find_song(title=track['Name'], artist=track.get('Artist',''), album=track.get('Album',''))
      if song is not None:
        new_playlist.write("\nFile{i}={path}\nTitle{i}={title}\n\n".format(i=i, path=song['file'], title=song['title']))
        i += 1

    new_playlist.write("NumberOfEntries={i}\nVersion=2\n".format(i=i))

elif screen == 'import-ratings':
  library = parse_library_xml()
  progress = xbmcgui.DialogProgress()
  progress.create(__addonname__, 'Importing Ratings')
  progress.update(1)
  num_tracks = float(len(library['Tracks']))
  i = 0
  for track in library['Tracks'].values():
    if progress.iscanceled():
      break
    progress.update(int(i/num_tracks*100))
    kind = track.get('Kind', '')
    rating = track.get('Rating', 0)
    if kind in ('MPEG audio file', 'Purchased AAC audio file', 'AAC audio file'):
      song = find_song(title=track['Name'], artist=track.get('Artist',''), album=track.get('Album',''))
      if song is not None and song.get('rating',0) != rating:
        result = json_rpc("AudioLibrary.SetSongDetails", songid=song['songid'], rating=rating)
    i += 1
  progress.close()


