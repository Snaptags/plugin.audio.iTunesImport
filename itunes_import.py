import xbmcaddon
import xbmcgui
import xbmcplugin
import urllib
import urlparse


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



print "base: {base}, handle:{handle} args:{args}".format(base=__base__, handle=__handle__, args=__args__)

def build_url(query):
    return "{base}?{query}".format(base=__base__, query=urllib.urlencode(query))


screen = __args__.get('screen', ['top'])[0]
print "screen: {0}".format(screen)

if screen == 'top':
  playlists_url = build_url({'screen': 'playlists'})
  import_playlist_item = xbmcgui.ListItem('Import Playlist', iconImage='DefaultFolder.png')
  xbmcplugin.addDirectoryItem(handle=__handle__, url=playlists_url, listitem=import_playlist_item, isFolder=True)
  xbmcplugin.endOfDirectory(handle=__handle__, succeeded=True)

elif screen == 'playlists':
  url = build_url({'screen': 'foo'})
  li = xbmcgui.ListItem('foo')
  xbmcplugin.addDirectoryItem(handle=__handle__, url=url, listitem=li)
  xbmcplugin.endOfDirectory(handle=__handle__, succeeded=True)
