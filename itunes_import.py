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
import sys
import codecs

# add ./resources/lib to sys.path 
lib_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources', 'lib')
sys.path.append(lib_path)

from koditunes import ITunesParser

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

  # End
  xbmcplugin.endOfDirectory(handle=__handle__, succeeded=True)

elif screen == 'playlists':

  itunes = ITunesParser(library_xml_path)
  for playlist in itunes.playlists.values():
      url = build_url({'screen': 'import-playlist', 'playlistId': playlist['Playlist ID']})
      li = xbmcgui.ListItem(playlist['Name'])
      xbmcplugin.addDirectoryItem(handle=__handle__, url=url, listitem=li)
  xbmcplugin.endOfDirectory(handle=__handle__, succeeded=True)

elif screen == 'import-playlist':
  playlist_id = __args__.get('playlistId')[0]

  itunes = ITunesParser(library_xml_path)
  playlist = itunes.playlists.get(playlist_id, None)
  if playlist:
    new_path = os.path.join(music_playlists_path, "{name}.pls".format(name=playlist['Name']))
    with codecs.open(new_path, 'w', encoding='utf8') as new_playlist:

      progress = xbmcgui.DialogProgress()
      progress.create(__addonname__, 'Creating Playlist')
      progress.update(1)
      track_count = float(len(playlist['Tracks']))

      new_playlist.write(u"[playlist]\n")
      i = 1
      for track in playlist['Tracks']:
        song = find_song(title=track['Name'], artist=track.get('Artist',''), album=track.get('Album',''))
        if song is not None:
          new_playlist.write(u"\nFile{i}={path}\nTitle{i}={title}\n\n".format(i=i, path=song['file'], title=song['title']))
          i += 1
        progress.update(int(i/track_count*100))
      new_playlist.write(u"NumberOfEntries={i}\nVersion=2\n".format(i=i))
      progress.close()

elif screen == 'import-ratings':
  itunes = ITunesParser(library_xml_path)
  library = itunes.plist

  progress = xbmcgui.DialogProgress()
  progress.create(__addonname__, 'Updating Ratings')
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


