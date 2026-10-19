"""Removes the language pie from the 3D contribution graph.

The action has no setting for that, and its pie counts per commit, so it showed
languages that the own stats card deliberately leaves out. The pie is the
top-level group placed at translate(40, ...), bottom left.
"""
import re, sys

path = sys.argv[1]
svg = open(path).read()
body_start = svg.index("</style>") + len("</style>")

depth, start = 0, None
for m in re.finditer(r"<(/?)([a-zA-Z]+)([^>]*?)(/?)>", svg[body_start:]):
    closing, tag, attrs, self_closing = m.groups()
    pos = body_start + m.start()
    if closing:
        depth -= 1
        if depth == 0 and start is not None:
            svg = svg[:start] + svg[pos + len(m.group(0)):]
            break
        continue
    if depth == 0 and tag == "g" and re.search(r'transform="translate\(40,', attrs):
        start = pos
    if not self_closing:
        depth += 1
else:
    sys.exit("pie group not found, layout of the action changed")

open(path, "w").write(svg)
