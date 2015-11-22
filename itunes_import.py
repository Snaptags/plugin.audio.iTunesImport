import xbmcaddon
import xbmcgui
import xbmcplugin


__handle__ = int(sys.argv[1])

url = ''
li = xbmcgui.ListItem('Library XML:')
xbmcplugin.addDirectoryItem(handle=__handle__, url=url, listitem=li)

xbmcplugin.endOfDirectory(handle=__handle__)
