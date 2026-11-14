"""Render the main menu icons (requires cairosvg): coloured tiles per menu group
with a white line glyph. No text is baked into the images; Kodi shows the label.

Run from the repository root:  python3 scripts/build-menu-icons.py
"""
from pathlib import Path

import cairosvg

OUT = Path(__file__).resolve().parents[1] / 'resources' / 'media' / 'menu'

# Menu groups share one colour so related entries are recognisable at a glance.
GROUP_COLORS = {
    'watch': '#2f5bd3',    # browsing the catalogue
    'mine': '#7a3fd1',     # the user's own lists and library
    'live': '#d1452f',     # live tv and the guide
    'account': '#3c3f4a',  # search, profiles, sign in/out
}

GLYPHS = {
    'search': ('account', '<circle cx="117" cy="115" r="37"/><path d="m145 143 34 34"/>'),
    'mylist': ('mine', '<path d="M78 88h64M78 118h64M78 148h40"/>'
                       '<path d="m166 128 9 19 21 3-15 15 4 21-19-10-19 10 4-21-15-15 21-3z"/>'),
    'watchlater': ('mine', '<circle cx="128" cy="128" r="54"/><path d="M128 96v34l24 15"/>'),
    'myseries': ('mine', '<path d="M92 77h72v107l-36-23-36 23z"/><path d="m110 117 13 13 23-25"/>'),
    'library': ('mine', '<rect x="78" y="78" width="24" height="94" rx="4"/>'
                        '<rect x="110" y="68" width="24" height="104" rx="4"/>'
                        '<path d="M86 96h8m24-12h8"/><path d="m145 88 22-7 26 85-22 7z"/><path d="M70 180h116"/>'),
    'series': ('watch', '<rect x="75" y="94" width="106" height="80" rx="10"/><path d="M88 80h80m-66-14h52"/>'
                        '<path d="m118 117 27 18-27 18z" fill="white" stroke="none"/>'),
    'tvshows': ('watch', '<rect x="72" y="91" width="112" height="79" rx="10"/><path d="m105 70 23 21 23-21m-40 116h34"/>'),
    'documentary': ('watch', '<circle cx="128" cy="128" r="54"/>'
                             '<path d="M74 128h108M128 74c-24 28-24 80 0 108M128 74c24 28 24 80 0 108"/>'),
    'movies': ('watch', '<rect x="73" y="84" width="110" height="92" rx="10"/>'
                        '<path d="M96 84v92m64-92v92M74 108h22m-22 44h22m64-44h22m-22 44h22"/>'
                        '<path d="m117 112 26 18-26 18z" fill="white" stroke="none"/>'),
    'tv': ('live', '<circle cx="128" cy="128" r="10"/>'
                   '<path d="M100 100a40 40 0 0 0 0 56M156 100a40 40 0 0 1 0 56M80 80a68 68 0 0 0 0 96M176 80a68 68 0 0 1 0 96"/>'),
    'epg': ('live', '<rect x="70" y="78" width="116" height="100" rx="10"/><path d="M70 106h116M98 78v100M112 128h28M112 152h52"/>'),
    'profiles': ('account', '<circle cx="128" cy="100" r="25"/><path d="M81 181v-9a47 38 0 0 1 94 0v9"/>'),
    'login': ('account', '<path d="M139 77h36v102h-36M75 128h69m-23-24 24 24-24 24"/>'),
    'logout': ('account', '<path d="M117 77H81v102h36m-5-51h69m-23-24 24 24-24 24"/>'),
}


def render(name, group, glyph, size=512):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 256 256">
<rect x="8" y="8" width="240" height="240" rx="52" fill="{GROUP_COLORS[group]}"/>
<g transform="translate(128 128) scale(1.12) translate(-128 -128)" fill="none" stroke="white" stroke-width="8"
   stroke-linecap="round" stroke-linejoin="round">{glyph}</g>
</svg>'''
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(OUT / f'{name}.png'))


if __name__ == '__main__':
    for name, (group, glyph) in GLYPHS.items():
        render(name, group, glyph)
    print('rendered', len(GLYPHS), 'icons to', OUT)
