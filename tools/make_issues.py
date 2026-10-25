#!/usr/bin/env python3
"""make_issues.py: opens one GitHub issue per listed game to hold its comments, and records the number in issues.json.

Run by the Action after index.json is built; needs the gh command and GH_TOKEN with issues: write. Games that already have an issue are skipped.
The portal reads and posts comments on these issues, so people comment from their own GitHub accounts and the keeper moderates on GitHub.
"""
import json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
repo = os.environ.get('GITHUB_REPOSITORY', '')


def load(p, d):
    try:
        return json.load(open(os.path.join(ROOT, p), encoding='utf-8'))
    except (OSError, ValueError):
        return d


def main():
    games = load('index.json', {}).get('games') or []
    issues = load('issues.json', {})
    changed = False
    for g in games:
        if issues.get(g['id']):
            continue
        body = ('Comments for the game "%s" (%s) in the Pin Portal game library.\n\nPeople comment from the Game library tab in their portal, which posts here from their own GitHub account. '
                'Be kind and keep it about the game.' % (g['name'], g['id']))
        r = subprocess.run(['gh', 'api', 'repos/%s/issues' % repo, '-f', 'title=Comments: %s (%s)' % (g['name'], g['id']), '-f', 'body=' + body],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print('could not open an issue for %s: %s' % (g['id'], (r.stderr or r.stdout).strip()[:200])); continue
        issues[g['id']] = json.loads(r.stdout)['number']; changed = True
        print('issue %d for %s' % (issues[g['id']], g['id']))
    if changed:
        with open(os.path.join(ROOT, 'issues.json'), 'w', encoding='utf-8') as f:
            json.dump(issues, f, indent=1); f.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
