"""library_check.py: the safety checks for a game zip from the game library (and for a zip about to be shared).

It uses only the Python standard library, so the portal and the games repository's check run the same file.

scan_zip(zf, standard=None) returns a dict:
  ok         False when anything in 'errors' was found (the game must not be installed or shared)
  errors     reasons the zip is refused, in plain words
  warnings   things worth knowing that do not block it
  code       the files that run as code (Python, JavaScript, HTML pages, shell scripts) and are not the standard ones from the Game Template
  id, name   from game.json
  files, bytes   how many files, and their size once unpacked

Hard refusals (nothing overrides them): paths that climb out of the folder, links, programs and libraries, any shell script other than the one start script,
a start script that reaches out to the network, uses sudo or touches system folders, a coil pulse longer than p2kd's own 150 ms cap, a zip over 50 MB,
over 3000 files or over 300 MB once unpacked.

Code is allowed but listed, because it runs on the cabinet or in its browser. The Game Template's own files (matched by their checksum) are not listed.
"""
import hashlib, json, os, posixpath, re

MAX_ZIP = 50 * 1024 * 1024
MAX_FILES = 3000
MAX_UNPACKED = 300 * 1024 * 1024
MAX_PULSE_MS = 150
ID_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,39}')
SAFE_EXT = {'.yaml', '.yml', '.json', '.md', '.txt', '.csv', '.cfg', '.ini', '.html', '.htm', '.js', '.css', '.py', '.sh',
            '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.woff', '.woff2', '.ttf', '.otf',
            '.pdf', '.mp3', '.wav', '.ogg', '.flac', '.m4a', '.mid', '.mp4', '.webm'}
CODE_EXT = {'.py', '.js', '.html', '.htm', '.sh', '.svg'}
SKIP_NAMES = {'.DS_Store', 'Thumbs.db'}
# the start script may start MPF, the display server and a browser. It must not use sudo, fetch from the network, open a shell for someone else or touch the system.
BAD_SCRIPT = re.compile(
    r'(?<![\w-])(sudo|wget|nc|ncat|netcat|ssh|scp|sftp|rsync|ftp|telnet|socat|eval|base64|crontab|systemctl|dd|mkfs|chown|useradd|visudo|iptables)(?![\w-])'
    r'|/etc/|/root\b|~/\.ssh|\.ssh/|/dev/(?!null)|python3?\s+-c|\bsh\s+-c|\bbash\s+-c|rm\s+-[a-zA-Z]*[rf][a-zA-Z]*\s+(/|~|\$HOME)|curl\s+(?!-s -m 2 -X POST -d \'\{"seconds":120\}\' http://localhost:8095/api/nav/pause)')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def standard_hashes(template_dir):
    """checksums of every file in the installed Game Template, so its own code is not listed as new code"""
    out = set()
    for root, _, fs in os.walk(template_dir):
        for f in fs:
            fp = os.path.join(root, f)
            if os.path.islink(fp) or not os.path.isfile(fp):
                continue
            try:
                out.add(sha256(open(fp, 'rb').read()))
            except OSError:
                pass
    return out


def _yaml_pulses(text):
    """default_pulse_ms and pulse_ms values found in a YAML file, read line by line (no YAML library needed)"""
    out = []
    for m in re.finditer(r'^\s*(?:default_)?pulse_ms\s*:\s*([0-9.]+)', text, re.M):
        try:
            out.append(float(m.group(1)))
        except ValueError:
            pass
    return out


def scan_zip(zf, standard=None, zip_size=None):
    standard = standard or set()
    r = {'ok': False, 'errors': [], 'warnings': [], 'code': [], 'id': '', 'name': '', 'files': 0, 'bytes': 0}
    err = r['errors'].append
    infos = [i for i in zf.infolist() if not i.is_dir()]
    if zip_size is not None and zip_size > MAX_ZIP:
        err('the zip is %d MB, the limit is %d MB (music is never part of a shared game)' % (zip_size // 1048576, MAX_ZIP // 1048576))
    if len(infos) > MAX_FILES:
        err('the zip holds %d files, the limit is %d' % (len(infos), MAX_FILES))
    r['files'] = len(infos); r['bytes'] = sum(i.file_size for i in infos)
    if r['bytes'] > MAX_UNPACKED:
        err('it is %d MB unpacked, the limit is %d MB' % (r['bytes'] // 1048576, MAX_UNPACKED // 1048576))
    if r['errors']:
        return r
    names = []
    for i in infos:
        n = i.filename.replace('\\', '/')
        parts = n.split('/')
        if n.startswith('/') or '..' in parts or re.match(r'^[A-Za-z]:', n):
            err('unsafe path: ' + n[:80]); continue
        if ((i.external_attr >> 28) & 0xF) == 0xA:
            err('a link inside the zip: ' + n[:80]); continue
        if posixpath.basename(n) in SKIP_NAMES or '.bak' in posixpath.basename(n) or n.endswith(('.log', '.pyc')):
            continue
        names.append((i, n))
    if r['errors']:
        return r
    tops = {n.split('/')[0] for _, n in names}
    prefix = ''
    if 'game.json' not in [n for _, n in names]:
        if len(tops) == 1 and (list(tops)[0] + '/game.json') in [n for _, n in names]:
            prefix = list(tops)[0] + '/'
        else:
            err('there is no game.json, so this is not a game'); return r
    try:
        man = json.loads(zf.read(prefix + 'game.json').decode('utf-8'))
        assert isinstance(man, dict)
    except Exception:
        err('game.json cannot be read'); return r
    gid = str(man.get('id') or prefix.strip('/') or '')
    if not ID_RE.fullmatch(gid) or gid in ('game-template', 'p2k-panel', 'p2k-bridge', 'pinbox'):
        err('the game id "%s" cannot be used (letters, digits and dashes, up to 40)' % gid[:50])
    r['id'] = gid; r['name'] = str(man.get('name') or gid)[:80]
    for i, n in names:
        rel = n[len(prefix):] if n.startswith(prefix) else n
        ext = posixpath.splitext(rel)[1].lower()
        mode = (i.external_attr >> 16) & 0o777
        top = '/' not in rel
        if ext not in SAFE_EXT:
            err('a file type that is not allowed: ' + rel[:80]); continue
        if ext == '.sh' and not (top and rel.startswith('start-')):
            err('only the start script (start-....sh in the game folder) may be a shell script: ' + rel[:80]); continue
        if mode & 0o111 and not (ext == '.sh' and top):
            err('a file marked as a program: ' + rel[:80]); continue
        data = zf.read(i)
        if ext == '.sh':
            txt = data.decode('utf-8', 'replace')
            code = re.sub(r'(?m)^\s*#.*$', '', txt)
            m = BAD_SCRIPT.search(code)
            if m:
                err('the start script %s uses "%s", which a shared game may not' % (rel, m.group(0).strip()[:40])); continue
        if ext in ('.yaml', '.yml'):
            for p in _yaml_pulses(data.decode('utf-8', 'replace')):
                if p > MAX_PULSE_MS:
                    err('%s sets a coil pulse of %g ms, the limit is %d ms' % (rel, p, MAX_PULSE_MS)); break
        if ext in CODE_EXT and sha256(data) not in standard:
            if ext == '.svg' and b'<script' not in data.lower():
                continue
            if ext in ('.html', '.htm') and b'<script' not in data.lower():
                continue
            r['code'].append(rel)
    if not any(posixpath.splitext(n)[1].lower() in ('.yaml', '.yml') for _, n in names):
        r['warnings'].append('no YAML files, so there are no modes or config in it')
    r['ok'] = not r['errors']
    return r
