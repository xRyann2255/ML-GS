"""Strings that must survive JSON armour without escaping the page.

check-bundle.js fails a bundle that contains a script tag with an src, an
@font-face, an @import or a closing script tag inside the payload, and
render.py splices between two literal markers -- one of which is spelled
out below. If any of these reaches the HTML unarmoured the artifact is
either not self-contained or does not render at all.
"""

PAYLOAD = [
    '<script src="https://x/y.js">',
    '</script>',
    '@font-face',
    '@import url(https://x/z.css)',
    '/* an opening block comment */',
    'RENDER — knows only',
    "</\u0073cript> and a literal backslash-u escape",
]


def settings():
    """A second dangling target: pkg.missing has no file on disk."""
    from pkg.missing import THING

    return THING
