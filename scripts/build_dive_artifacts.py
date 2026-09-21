#!/usr/bin/env python3
"""Assemble the standalone artifact copy of each deep-dive explainer.

The explainers live in _includes so Jekyll can serve them at /notes/..., and
the same body is published as a Claude artifact. This resolves the one Liquid
include they use, strips the header comments, and prepends the artifact title,
so there is a single source for both hosts.

    python3 scripts/build_dive_artifacts.py [out_dir]
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCLUDES = os.path.join(BASE, '_includes')

DIVES = [
    ('atlas-explainer.html', 'Atlas Teardown', 'atlas_teardown.html'),
    ('vjepa-explainer.html', 'V-JEPA Teardown', 'vjepa_teardown.html'),
]

COMMENT = re.compile(r"\{%-?\s*comment\s*-?%\}.*?\{%-?\s*endcomment\s*-?%\}\s*", re.S)
INCLUDE = re.compile(r"\{%\s*include\s+([\w.-]+)\s*%\}")


def resolve(name, depth=0):
    if depth > 4:
        raise RuntimeError('include nesting too deep at %s' % name)
    text = open(os.path.join(INCLUDES, name), encoding='utf-8').read()
    text = COMMENT.sub('', text)
    return INCLUDE.sub(lambda m: resolve(m.group(1), depth + 1), text)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else BASE
    for source, title, filename in DIVES:
        body = resolve(source)
        leftover = re.findall(r'\{%|\{\{', body)
        if leftover:
            raise SystemExit('%s: unresolved Liquid in the artifact copy' % source)
        path = os.path.join(out_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('<title>%s</title>\n%s' % (title, body))
        print('%-24s -> %s (%d bytes, %d style, %d script)'
              % (source, path, len(body), body.count('<style>'), body.count('<script>')))


if __name__ == '__main__':
    main()
