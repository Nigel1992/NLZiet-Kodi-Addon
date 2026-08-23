from resources.lib.kodi import ui


class FakeListItem:
    def __init__(self, label, offscreen):
        self.label = label
        self.offscreen = offscreen
        self.art = []
        self.properties = {}
        self.info = []
        self.context_menu = []

    def setArt(self, art):
        self.art.append(art)

    def setProperty(self, key, value):
        self.properties[key] = value

    def setInfo(self, kind, info):
        self.info.append((kind, info))

    def setLabel2(self, value):
        self.label2 = value

    def addContextMenuItems(self, items):
        self.context_menu.extend(items)


class FakeAddon:
    def getAddonInfo(self, key):
        return 'C:/addon' if key == 'path' else ''


def test_build_url_preserves_plugin_base_and_query_encoding():
    assert ui.build_url('plugin://plugin.video.nlziet', {'q': 'space query'}) == (
        'plugin://plugin.video.nlziet?q=space+query'
    )


def test_add_directory_item_marks_playable_items_and_preserves_url(monkeypatch):
    items = []
    added = []
    monkeypatch.setattr(
        ui.xbmcgui,
        'ListItem',
        lambda **kwargs: items.append(FakeListItem(**kwargs)) or items[-1],
        raising=False,
    )
    monkeypatch.setattr(ui.os.path, 'exists', lambda path: False)
    monkeypatch.setattr(
        ui.xbmcplugin,
        'addDirectoryItem',
        lambda handle, url, item, isFolder: added.append((handle, url, item, isFolder)),
        raising=False,
    )

    ui.add_directory_item(
        FakeAddon(),
        42,
        lambda query: ui.build_url('plugin://plugin.video.nlziet', query),
        lambda: None,
        'Episode',
        {'mode': 'play', 'id': 'e1'},
        is_folder=False,
        thumb='https://image.test/poster.jpg',
    )

    assert added[0][0] == 42
    assert added[0][1] == 'plugin://plugin.video.nlziet?mode=play&id=e1'
    assert added[0][3] is False
    assert items[0].properties['IsPlayable'] == 'true'
    assert items[0].art[-1]['thumb'] == 'https://image.test/poster.jpg'


def test_artwork_helpers_prefer_landscape_for_fanart_and_portrait_for_poster():
    item = FakeListItem('Title', True)

    ui.set_smart_artwork(item, {
        'landscapeUrl': 'https://image.test/landscape.jpg',
        'portraitUrl': 'https://image.test/portrait.jpg',
    })

    assert item.art == [{
        'fanart': 'https://image.test/landscape.jpg?width=3840',
        'landscape': 'https://image.test/landscape.jpg?width=3840',
        'poster': 'https://image.test/portrait.jpg?width=3840',
        'thumb': 'https://image.test/landscape.jpg?width=3840',
        'icon': 'https://image.test/landscape.jpg?width=3840',
    }]
