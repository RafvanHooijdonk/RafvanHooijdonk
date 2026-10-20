"""Removes the language pie from the 3D contribution graph and adds a colour legend.

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
    print("pie group not found (already removed, or the action changed its layout)")

# Legend in the freed spot: the five colour levels, using the graph's own classes so the
# colours follow light and dark mode by themselves.
squares = "".join(
    f'<rect x="{66 + i * 36}" y="-21" width="28" height="28" rx="5" class="cont-top-{i}"/>' for i in range(5))
legend = (
    '<g id="legend" transform="translate(40, 700)">'
    '<text x="0" y="-44" style="font-size: 22px;" class="fill-fg">Contributions per day</text>'
    '<text x="0" y="0" style="font-size: 17px;" class="fill-weak">Less</text>'
    f'{squares}'
    '<text x="256" y="0" style="font-size: 17px;" class="fill-weak">More</text>'
    '<text x="0" y="40" style="font-size: 17px;" class="fill-weak">Bar height is the number of contributions that day</text>'
    '</g>')
if 'id="legend"' not in svg:
    svg = svg.replace("</svg>", legend + "</svg>")

open(path, "w").write(svg)
