import xbmcaddon
import xbmcgui
import xbmcplugin
import urllib
import urlparse
import plistlib
import StringIO
import sys


__base__ = sys.argv[0]
__handle__ = int(sys.argv[1])
__args__ = urlparse.parse_qs(sys.argv[2][1:])


__addon__ = xbmcaddon.Addon(id="plugin.audio.iTunesImport")
__addonname__ = __addon__.getAddonInfo('name')
__addonid__ = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')


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
  progress.create('Foobar', 'Parsing library plist')
  progress.update(25)
  plist = plistlib.readPlist(library_xml_path)
  progress.close()
  return plist




if screen == 'top':
  playlists_url = build_url({'screen': 'playlists'})
  import_playlist_item = xbmcgui.ListItem('Import Playlist', iconImage='DefaultFolder.png')
  xbmcplugin.addDirectoryItem(handle=__handle__, url=playlists_url, listitem=import_playlist_item, isFolder=True)
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
  print "playlist: {0}".format(playlist)
