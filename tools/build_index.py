#!/usr/bin/env python3
"""build_index.py: checks every game in games/ and writes index.json, the list the Pin Portal reads.

  python3 tools/build_index.py            rebuild index.json (a game that fails the check is left out and the run fails)
  python3 tools/build_index.py --check    only check, write nothing (used on pull requests)
  --template DIR                          a checkout of the Game Template, so its own files are not listed as new code

Each game is games/<id>/<id>.zip with games/<id>/info.json and an optional screenshot.png.
info.json carries version and min_portal (the oldest Pin Portal the game works with, or empty for any); they must match game.json inside the zip.
A game that was already listed may only be replaced by a higher version (checked against the old index.json).
reviewed.json is {id: sha256 of the zip a maintainer has read}; a game is "reviewed" only while its zip still has that checksum.
"""
import datetime, hashlib, json, os, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import library_check as lc


def load(path, default):
    try:
        return json.load(open(path, encoding='utf-8'))
    except (OSError, ValueError):
        return default


def _newer(a, b):
    x = [int(n) for n in a.split('.')]; y = [int(n) for n in b.split('.')]
    n = max(len(x), len(y)); x += [0] * (n - len(x)); y += [0] * (n - len(y))
    return x > y


def main():
    check_only = '--check' in sys.argv
    standard = set()
    if '--template' in sys.argv:
        t = sys.argv[sys.argv.index('--template') + 1]
        if os.path.isdir(t):
            standard = lc.standard_hashes(t)
    reviewed = load(os.path.join(ROOT, 'reviewed.json'), {})
    old = {g.get('id'): g for g in (load(os.path.join(ROOT, 'index.json'), {}).get('games') or []) if isinstance(g, dict)}
    today = datetime.date.today().isoformat()
    out, bad = [], 0
    gdir = os.path.join(ROOT, 'games')
    for gid in sorted(os.listdir(gdir)) if os.path.isdir(gdir) else []:
        d = os.path.join(gdir, gid)
        if not os.path.isdir(d):
            continue
        zp = os.path.join(d, gid + '.zip')
        info = load(os.path.join(d, 'info.json'), None)
        if not os.path.isfile(zp) or not isinstance(info, dict):
            print('FAIL %s: needs %s.zip and info.json' % (gid, gid)); bad += 1; continue
        raw = open(zp, 'rb').read()
        try:
            with zipfile.ZipFile(zp) as zf:
                res = lc.scan_zip(zf, standard, len(raw))
        except zipfile.BadZipFile:
            print('FAIL %s: not a zip file' % gid); bad += 1; continue
        if not res['ok']:
            print('FAIL %s: %s' % (gid, '; '.join(res['errors']))); bad += 1; continue
        if res['id'] != gid:
            print('FAIL %s: game.json says the id is %s' % (gid, res['id'])); bad += 1; continue
        ver = str(info.get('version') or res['version'] or '')
        minp = str(info.get('min_portal') or res['min_portal'] or '')
        bad_v = [k for k, v in (('version', ver), ('min_portal', minp)) if v and not lc.VER_RE.fullmatch(v)]
        if bad_v:
            print('FAIL %s: %s is not a version number like 1.2' % (gid, ', '.join(bad_v))); bad += 1; continue
        if not ver:
            print('FAIL %s: no version in info.json or game.json' % gid); bad += 1; continue
        if res['version'] and res['version'] != ver:
            print('FAIL %s: info.json says version %s but game.json in the zip says %s' % (gid, ver, res['version'])); bad += 1; continue
        if res['min_portal'] != minp:
            print('FAIL %s: info.json says min_portal "%s" but game.json in the zip says "%s"' % (gid, minp, res['min_portal'])); bad += 1; continue
        sha = lc.sha256(raw)
        prev = old.get(gid) or {}
        if prev.get('sha256') and prev['sha256'] != sha and prev.get('version') and not _newer(ver, prev['version']):
            print('FAIL %s: the zip changed but version %s is not higher than the listed %s' % (gid, ver, prev['version'])); bad += 1; continue
        out.append({'id': gid, 'name': str(info.get('name') or res['name'])[:80], 'author': str(info.get('author') or '')[:40],
                    'about': str(info.get('about') or '')[:600], 'hardware': str(info.get('hardware') or '')[:12],
                    'licence': str(info.get('licence') or '')[:60], 'version': ver[:20], 'min_portal': minp[:20],
                    'bytes': len(raw), 'sha256': sha, 'reviewed': reviewed.get(gid) == sha, 'code': res['code'][:40],
                    'screenshot': os.path.isfile(os.path.join(d, 'screenshot.png')),
                    'updated': prev.get('updated') if prev.get('sha256') == sha and prev.get('updated') else today})
        print('ok   %s (%d KB, %d code files, %s)' % (gid, len(raw) // 1024, len(res['code']), 'reviewed' if out[-1]['reviewed'] else 'not reviewed'))
    if not check_only:
        with open(os.path.join(ROOT, 'index.json'), 'w', encoding='utf-8') as f:
            json.dump({'games': out}, f, indent=1)
            f.write('\n')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
