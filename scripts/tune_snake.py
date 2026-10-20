"""Tunes the snake animation after Platane/snk made it.

The action only takes colours, so speed and dot shape are set here:
the loop runs faster and the dots get the rounder corners of the README cards.
"""
import re, sys

SPEED = 0.67      # loop duration factor: about 60 s becomes about 40 s
DOT_RADIUS = 4    # dots are 12 px, the action draws them with radius 2

for path in sys.argv[1:]:
    svg = open(path).read()
    svg = re.sub(r"(\d+)ms", lambda m: f"{round(int(m.group(1)) * SPEED)}ms", svg)
    svg = svg.replace('rx="2" ry="2"', f'rx="{DOT_RADIUS}" ry="{DOT_RADIUS}"')
    open(path, "w").write(svg)
    print(path, "tuned")
