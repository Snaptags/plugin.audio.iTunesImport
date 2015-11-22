import xbmcaddon
import xbmcgui

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__addonid__ = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')


xbmcgui.Dialog().ok(__addonname__, "Hello, iTunes Import v{0}!".format(__addonversion__))