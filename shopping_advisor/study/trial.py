"""Controlled execution of an adaptation: capture, inspect, run inside a boundary.

R15. The :mod:`adaptation` record says what an engineering operation inside a
study was; this module is the controlling procedure that fills it in, and it
runs on the trusted side -- the maintainer's checkout -- never inside the trial
tree it examines. Three things happen here, in this order, and nothing is
imported from the patch before the first two are done.

**Capture.** The patch is the difference between a base tree and a worktree,
file by file, with the full content of every added or modified file, the
digest of both trees and of the lock. A dirty flag reproduces no code and a
commit in a disposable worktree outlives nothing; the archive does.

**Inspect, statically.** Before any import, the changed Python is parsed and
read for module-level statements that do work at import time, for the names
that reach the network or spawn processes, for file writes, for changes to a
published version constant, to dependencies and to the *evaluator set* -- the
maintenance gate, its test module and its baseline, the project file and the
lock. A patch that touches the evaluator set is not executed here at all: it
goes through ordinary maintenance, because a gate a patch may rewrite cannot
judge the patch. The evaluator set in the trial tree must be byte-identical to
the base revision's before a check runs, and that is verified, not assumed.

**Execute inside a declared boundary.** One runner profile: a git worktree for
files, the locked virtual environment for dependencies, and a
``sandbox-exec`` profile denying everything by default -- reads only of the
tree, the environment and the system, writes only under one scratch directory,
no network -- with a watchdog that kills the whole process group at the
timeout. Every check records the boundary it ran under. Where the kernel
profile cannot be demonstrated (see :func:`available`), the honest label is
``harness-only`` and it is an exception the maintainer records; nothing here
presents a weaker mode as the demonstrated one.

Apple marks ``sandbox-exec`` deprecated; it is present on macOS today and this
module says so rather than promising portability (ROADMAP R17). Inside the
profile ``git`` does not run -- its shim writes a cache under ``TMPDIR`` and
reads the user's configuration -- which is why identity is computed here, on
the trusted side, and never by code inside the boundary.
"""

import ast
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from ..provenance import sha256_file, sha256_text
from . import adaptation

#: Paths a trial patch may not touch: the evaluator judges the patch, so the
#: patch does not get to change the evaluator. Relative to the tree root.
EVALUATOR_SET = ('shopping_advisor/maintenance', 'tests/test_maintenance.py',
                 'pyproject.toml', 'uv.lock')
#: Directories that are never part of a tree's identity.
IGNORED = {'.git', '.venv', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache',
           'data', 'reports', '.DS_Store'}
#: The one write the suite needs beside the committed fixtures: six test
#: modules write temporary briefs there because a brief's inputs are relative
#: to the brief file. Measured on 2026-09-18; a boundary decision, stated.
FIXTURE_TEMP = 'tests/studies/.tmp-'
SANDBOX = '/usr/bin/sandbox-exec'

NETWORK_MODULES = {'socket', 'urllib', 'urllib.request', 'http', 'http.client', 'requests',
                   'ssl', 'ftplib', 'smtplib', 'asyncio', 'twisted', 'scrapy'}
PROCESS_MODULES = {'subprocess', 'pty', 'multiprocessing'}
PROCESS_CALLS = {'os.system', 'os.popen', 'os.exec', 'os.spawn', 'os.fork', 'os.posix_spawn'}
WRITE_CALLS = {'write_text', 'write_bytes', 'os.remove', 'os.unlink', 'os.rename', 'os.replace',
               'shutil.rmtree', 'shutil.copy', 'shutil.move', 'os.makedirs', 'os.mkdir',
               'write_json_atomically'}
VERSION_LINE = re.compile(r'^\s*[A-Z_]*VERSION\s*=\s*\d+', re.M)


class TrialError(ValueError):
    """The trial cannot proceed as asked, and this says why."""


def _now():
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# Trees and their identity
# ---------------------------------------------------------------------------

def tree_files(root):
    """Every file that is part of the tree, relative, sorted.

    Git's view when it answers (tracked plus untracked, minus ignored); a walk
    that skips the working directories otherwise. Both exclude ``data/`` and
    ``reports/``: outputs are not the method.
    """
    root = Path(root)
    try:
        done = subprocess.run(('git', 'ls-files', '-c', '-o', '--exclude-standard', '-z'),
                              cwd=root, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        done = None
    if done is not None and done.returncode == 0:
        names = [n for n in done.stdout.decode('utf-8').split('\0') if n]
        return sorted(n for n in names if not _ignored(n) and (root / n).is_file())
    found = []
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORED)
        for name in filenames:
            relative = str(Path(directory, name).relative_to(root))
            if not _ignored(relative):
                found.append(relative)
    return sorted(found)


def _ignored(relative):
    return any(part in IGNORED for part in Path(relative).parts)


def tree_digest(root, files=None):
    """One digest over every file's path and content digest."""
    root = Path(root)
    files = tree_files(root) if files is None else files
    rows = [{'path': name, 'sha256': sha256_file(root / name)} for name in files]
    return sha256_text(json.dumps(rows, sort_keys=True, separators=(',', ':')))


def git_revision(root):
    try:
        done = subprocess.run(('git', 'rev-parse', 'HEAD'), cwd=root, capture_output=True,
                              text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ''
    return done.stdout.strip() if done.returncode == 0 else ''


def evaluator_files(root):
    """The evaluator set as it exists in this tree, relative, sorted."""
    root = Path(root)
    found = []
    for entry in EVALUATOR_SET:
        path = root / entry
        if path.is_file():
            found.append(entry)
        elif path.is_dir():
            found.extend(str(p.relative_to(root)) for p in sorted(path.rglob('*'))
                         if p.is_file() and not _ignored(str(p.relative_to(root))))
    return sorted(found)


def evaluator_digest(root):
    return tree_digest(root, evaluator_files(root))


def in_evaluator_set(relative):
    return any(relative == entry or relative.startswith(entry.rstrip('/') + '/')
               for entry in EVALUATOR_SET)


# ---------------------------------------------------------------------------
# Capture: the patch as a complete archive
# ---------------------------------------------------------------------------

def capture(base_root, worktree):
    """The difference between two trees, with full content, and both identities."""
    base_root, worktree = Path(base_root), Path(worktree)
    base_files = {name: sha256_file(base_root / name) for name in tree_files(base_root)}
    trial_files = {name: sha256_file(worktree / name) for name in tree_files(worktree)}
    files = []
    for name in sorted(set(base_files) | set(trial_files)):
        if name not in trial_files:
            files.append(adaptation.file_entry(name, 'deleted'))
        elif name not in base_files:
            files.append(adaptation.file_entry(name, 'added', (worktree / name).read_bytes()))
        elif base_files[name] != trial_files[name]:
            files.append(adaptation.file_entry(name, 'modified', (worktree / name).read_bytes()))
    lock = worktree / 'uv.lock'
    return {
        'base': {'git_revision': git_revision(base_root),
                 'tree_sha256': tree_digest(base_root, sorted(base_files))},
        'files': files,
        'result_tree_sha256': tree_digest(worktree, sorted(trial_files)),
        'lock_sha256': sha256_file(lock) if lock.is_file() else '',
        'evaluator': {'files': evaluator_files(base_root),
                      'base_sha256': evaluator_digest(base_root),
                      'frozen': evaluator_digest(base_root) == evaluator_digest(worktree)},
    }


def apply_patch(files, root):
    """Reconstruct a tree state from an archive: the rollback and the replay path."""
    root = Path(root)
    for entry in files:
        target = root / entry['path']
        if entry['status'] == 'deleted':
            if target.exists():
                target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(adaptation.file_content(entry))


# ---------------------------------------------------------------------------
# Static inspection, before the first import
# ---------------------------------------------------------------------------

def _dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    # A chain hanging off a call -- Path("x").write_text(...) -- keeps its
    # attribute names: the leaf is what the inspection looks at.
    return '.'.join(reversed(parts))


def _inspect_python(path, source, flags):
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        flags['import_side_effects'].append(f'{path}: does not parse ({exc.msg}, line {exc.lineno})')
        return
    for node in tree.body:
        harmless = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef,
                    ast.ClassDef, ast.Assign, ast.AnnAssign, ast.AugAssign)
        if isinstance(node, ast.Expr) and isinstance(getattr(node, 'value', None), ast.Constant):
            continue
        if isinstance(node, ast.If) and 'main' in ast.unparse(node.test):
            continue
        if not isinstance(node, harmless):
            flags['import_side_effects'].append(
                f'{path}:{node.lineno}: {type(node).__name__} at module level')
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)) and any(
                isinstance(sub, ast.Call) for sub in ast.walk(node.value or ast.Pass())):
            call = next(sub for sub in ast.walk(node.value) if isinstance(sub, ast.Call))
            name = _dotted(call.func)
            if name and name.split('.')[-1] not in {'compile', 'namedtuple', 'dataclass', 'field',
                                                    'frozenset', 'tuple', 'dict', 'set', 'list',
                                                    'Path', 'getLogger', 'MappingProxyType', 'str',
                                                    'int', 'float', 'sorted', 'join', 'get', 'object'}:
                flags['import_side_effects'].append(f'{path}:{node.lineno}: calls {name}() at import')
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split('.')[0]
                if alias.name in NETWORK_MODULES or top in NETWORK_MODULES:
                    flags['network'].append(f'{path}:{node.lineno}: import {alias.name}')
                if alias.name in PROCESS_MODULES or top in PROCESS_MODULES:
                    flags['subprocess'].append(f'{path}:{node.lineno}: import {alias.name}')
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split('.')[0]
            if node.module in NETWORK_MODULES or top in NETWORK_MODULES:
                flags['network'].append(f'{path}:{node.lineno}: from {node.module} import ...')
            if node.module in PROCESS_MODULES or top in PROCESS_MODULES:
                flags['subprocess'].append(f'{path}:{node.lineno}: from {node.module} import ...')
        elif isinstance(node, ast.Call):
            name = _dotted(node.func)
            leaf = name.split('.')[-1] if name else ''
            if name in PROCESS_CALLS or name.startswith('subprocess.') \
                    or any(name.startswith(p) for p in ('os.exec', 'os.spawn')):
                flags['subprocess'].append(f'{path}:{node.lineno}: {name}()')
            if name in WRITE_CALLS or leaf in {'write_text', 'write_bytes', 'write_json_atomically'}:
                flags['file_writes'].append(f'{path}:{node.lineno}: {name}()')
            if leaf == 'open' and len(node.args) > 1 and isinstance(node.args[1], ast.Constant) \
                    and any(ch in str(node.args[1].value) for ch in 'wax+'):
                flags['file_writes'].append(f'{path}:{node.lineno}: open(..., {node.args[1].value!r})')
            for keyword in node.keywords:
                if keyword.arg == 'mode' and isinstance(keyword.value, ast.Constant) \
                        and any(ch in str(keyword.value.value) for ch in 'wax+'):
                    flags['file_writes'].append(f'{path}:{node.lineno}: mode={keyword.value.value!r}')


def inspect(files, base_root=None):
    """Read the patch before running any of it. Returns the record's ``inspection``."""
    flags = {flag: [] for flag in adaptation.INSPECTION_FLAGS}
    paths = []
    for entry in files:
        path = entry['path']
        paths.append(f'{entry["status"]} {path}')
        if in_evaluator_set(path):
            flags['evaluator'].append(path)
        if path in ('pyproject.toml', 'uv.lock') or path.startswith('requirements'):
            flags['dependencies'].append(path)
        if entry['status'] == 'deleted':
            continue
        content = adaptation.file_content(entry)
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            continue
        if path.endswith('.py'):
            _inspect_python(path, text, flags)
            new_versions = set(VERSION_LINE.findall(text))
            old_versions = set()
            if base_root is not None and entry['status'] == 'modified' \
                    and (Path(base_root) / path).is_file():
                old_versions = set(VERSION_LINE.findall(
                    (Path(base_root) / path).read_text(encoding='utf-8', errors='replace')))
            for line in sorted(new_versions - old_versions):
                flags['contracts'].append(f'{path}: {line.strip()}')
    findings = []
    if flags['evaluator']:
        findings.append('the patch touches the evaluator set (' + ', '.join(flags['evaluator'])
                        + '): it is not executed as an adaptation; a change to the gate, its '
                          'test or the baseline goes through ordinary maintenance')
    if flags['dependencies']:
        findings.append('the patch changes dependencies: explicit scope and review, and a '
                        'runtime change stays separate from a behaviour change')
    if flags['network']:
        findings.append('the patch reaches for the network: an offline check must not need it, '
                        'and the boundary will refuse it')
    if flags['import_side_effects']:
        findings.append('the patch does work at import time; read those lines before importing')
    return {'paths': paths, 'flags': flags, 'findings': findings}


# ---------------------------------------------------------------------------
# The boundary
# ---------------------------------------------------------------------------

def interpreter_root(interpreter):
    """The directory tree the interpreter and its standard library live in."""
    real = Path(os.path.realpath(interpreter))
    # .../cpython-3.14.6-macos-aarch64-none/bin/python3.14 -> the distribution root
    return str(real.parent.parent)


def profile(worktree, scratch, interpreter, venv, extra_read=()):
    """The ``sandbox-exec`` profile: deny by default, then exactly what a check needs."""
    worktree, scratch = str(Path(worktree).resolve()), str(Path(scratch).resolve())
    reads = ['/', '/usr', '/System', '/Library', '/private/etc', '/private/var/db', '/dev',
             worktree, interpreter_root(interpreter), str(Path(venv).resolve()), *extra_read]
    read_rules = ' '.join(f'(subpath "{path}")' if path != '/' else '(literal "/")'
                          for path in dict.fromkeys(reads))
    return '\n'.join((
        '(version 1)',
        '(deny default)',
        '(allow process-exec* process-fork signal sysctl-read mach-lookup)',
        '(allow file-read-metadata)',
        f'(allow file-read* {read_rules})',
        f'(allow file-write* (subpath "{scratch}") (subpath "/dev") '
        f'(regex #"^{re.escape(worktree)}/{re.escape(FIXTURE_TEMP)}"))',
        '(deny network*)',
        '',
    ))


def available():
    """Can this machine run a kernel profile at all? Measured, not assumed."""
    if not Path(SANDBOX).is_file():
        return False
    try:
        done = subprocess.run((SANDBOX, '-p', '(version 1) (allow default) (deny network*)',
                               '/usr/bin/true'), capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def execute(argv, worktree, scratch, timeout, profile_path=None, interpreter='',
            boundary='kernel', env=None):
    """Run one check and return its record; kill the whole group at the timeout.

    ``boundary`` is ``kernel`` when ``profile_path`` wraps the command, and
    ``harness-only`` when the maintainer recorded an exception and the command
    runs bare. The record says which; nothing here upgrades the label.
    """
    worktree, scratch = Path(worktree), Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    tmpdir = scratch / 'tmp'
    tmpdir.mkdir(exist_ok=True)
    if boundary == 'kernel' and not profile_path:
        raise TrialError('a kernel boundary needs a profile; without one the label is a lie')
    command = [str(a) for a in argv]
    wrapped = [SANDBOX, '-f', str(profile_path), *command] if boundary == 'kernel' else command
    environment = {'PATH': '/usr/bin:/bin', 'TMPDIR': str(tmpdir), 'HOME': str(scratch),
                   'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
                   'PYTHONHASHSEED': '0'}
    if interpreter:
        environment['PATH'] = f'{Path(interpreter).parent}:' + environment['PATH']
    environment.update(env or {})
    started = _now()
    clock = _dt.datetime.now(_dt.timezone.utc)
    output_path = scratch / f'check-{clock.strftime("%Y%m%dT%H%M%SZ")}.log'
    timed_out, status = False, None
    with output_path.open('wb') as log:
        process = subprocess.Popen(wrapped, cwd=worktree, env=environment, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            status = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_group(process)
    finished = _dt.datetime.now(_dt.timezone.utc)
    seconds = round((finished - clock).total_seconds(), 3)
    return {
        'command': command, 'started_at': started,
        'finished_at': finished.replace(microsecond=0).isoformat(),
        'seconds': seconds, 'exit': None if timed_out else status, 'timed_out': timed_out,
        'output_sha256': sha256_file(output_path), 'output_path': str(output_path),
        'summary': ('killed at the timeout; an unfinished check has no pass' if timed_out
                    else f'exit {status}'),
        'boundary': boundary,
    }


def _kill_group(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def group_alive(pid):
    """Does any process in this group still exist? For the timeout test."""
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


PROBE = r'''
import json, pathlib, socket, sys
outside, worktree = sys.argv[1], sys.argv[2]
def probe(fn):
    try:
        fn(); return 'allowed'
    except PermissionError:
        return 'blocked'
    except Exception as exc:
        return 'error:' + type(exc).__name__
print(json.dumps({
    'read_outside': probe(lambda: pathlib.Path(outside, 'marker.txt').read_text()),
    'write_outside': probe(lambda: pathlib.Path(outside, 'probe-out.txt').write_text('x')),
    'write_tree': probe(lambda: pathlib.Path(worktree, 'probe-tree.txt').write_text('x')),
    'write_scratch': probe(lambda: pathlib.Path(sys.argv[3], 'probe-ok.txt').write_text('x')),
    'network': probe(lambda: socket.create_connection(('127.0.0.1', 9), timeout=1)),
    'read_home': probe(lambda: __import__('os').listdir(sys.argv[4])),
}))
'''
EXPECTED_PROBE = {'read_outside': 'blocked', 'write_outside': 'blocked', 'write_tree': 'blocked',
                  'write_scratch': 'allowed', 'network': 'blocked', 'read_home': 'blocked'}


def probe(worktree, scratch, interpreter, venv, outside, home=None):
    """Demonstrate the boundary with failure cases; the record of what was tried."""
    worktree, scratch, outside = Path(worktree), Path(scratch), Path(outside)
    scratch.mkdir(parents=True, exist_ok=True)
    outside.mkdir(parents=True, exist_ok=True)
    (outside / 'marker.txt').write_text('marker: a read of this proves the boundary leaks\n')
    profile_path = scratch / 'profile.sb'
    profile_path.write_text(profile(worktree, scratch, interpreter, venv), encoding='utf-8')
    script = scratch / 'probe.py'
    script.write_text(PROBE, encoding='utf-8')
    home = str(home or Path(os.path.expanduser('~')))
    check = execute([interpreter, str(script), str(outside), str(worktree), str(scratch), home],
                    worktree, scratch, timeout=60, profile_path=profile_path,
                    interpreter=interpreter)
    output = Path(check['output_path']).read_text(encoding='utf-8', errors='replace').strip()
    try:
        results = json.loads(output.splitlines()[-1]) if output else {}
    except ValueError:
        results = {}
    leaked = (worktree / 'probe-tree.txt').exists() or (outside / 'probe-out.txt').exists()
    return {'results': results, 'expected': EXPECTED_PROBE, 'leaked': leaked,
            'demonstrated': results == EXPECTED_PROBE and not leaked and check['exit'] == 0,
            'check': check, 'profile_sha256': sha256_file(profile_path)}
