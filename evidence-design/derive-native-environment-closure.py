"""Read-only static file/ELF closure derivation; no target executable is run.

No project module, test, fixture, bytecode, ELF, shared library or command under
inspection is imported or executed. Only the metadata manifest is written.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import struct

ROOT = Path('/workspace/shared/worker38-implementation')
OUT = ROOT / 'evidence-design/NATIVE-ENVIRONMENT-CLOSURE-06.json'
NATIVE_OUTPUT_ROOT = '/workspace/shared/worker38-native-batch-04'
LITERAL_RECIPE_SOURCE = 'evidence-design/derive-worker38-all-literal-pins.py'
STDLIB = Path('/usr/lib/python3.13')

if OUT.exists() or OUT.is_symlink():
    raise SystemExit('exclusive attempt06 environment evidence already exists')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode('ascii')


def pin(path):
    path = Path(path)
    if not os.path.lexists(path):
        return {'path': str(path), 'exists': False}
    info = path.lstat()
    row = {'path': str(path), 'exists': True, 'mode': stat.S_IMODE(info.st_mode)}
    if path.is_symlink():
        target = os.readlink(path)
        row.update(type='symlink', target=target, target_bytes_sha256=sha(os.fsencode(target)),
                   resolved=str(path.resolve()))
    elif path.is_dir():
        row['type'] = 'directory'
        return row
    else:
        assert stat.S_ISREG(info.st_mode), path
        row['type'] = 'file'
    if path.is_file():
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
        assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), path
        row.update(size_bytes=len(raw), sha256=sha(raw), mtime_ns=after.st_mtime_ns)
    return row


def inventory(directory):
    rows = []
    for path in sorted(Path(directory).rglob('*')):
        if path.is_file() or path.is_symlink():
            value = pin(path)
            rows.append([str(path.relative_to(directory)), value['type'], value.get('size_bytes'),
                         value.get('sha256'), value.get('mtime_ns'), value.get('target'), value.get('resolved')])
    return {'root': str(directory), 'columns': ['relative_path', 'type', 'size_bytes',
             'sha256', 'mtime_ns', 'symlink_target', 'resolved_symlink_target'],
            'entries': rows, 'entry_count': len(rows), 'manifest_sha256': sha(canonical(rows))}


def namespace(directory, import_only=False):
    path = Path(directory)
    if not path.is_dir():
        return {'root': str(path), 'exists': False}
    entries = []
    for child in sorted(path.iterdir()):
        if import_only and not (child.suffix in ('.py', '.pyc', '.so') or
                                (child.is_dir() and child.name.isidentifier())):
            continue
        kind = 'symlink' if child.is_symlink() else 'directory' if child.is_dir() else 'file'
        entries.append([child.name, kind, os.readlink(child) if child.is_symlink() else None])
    return {'root': str(path), 'exists': True, 'entries': entries,
            'scope': 'Python candidate files/directories only; non-importable reports excluded' if import_only else 'all immediate entries',
            'entries_sha256': sha(canonical(entries))}


PROJECT_NAMESPACE_POLICY = {
    'recursive': True,
    'follow_symlinks': False,
    'symlinks_allowed': False,
    'special_nodes_allowed': False,
    'non_ascii_names_allowed': False,
    'candidate_file_suffixes': ['.py', '.pyc', '.so'],
    'directory_rule': 'name.isidentifier() (includes __pycache__)',
}


def project_namespace(directory):
    """Finite lstat-only candidate roster; no source reads and no link traversal."""
    root = Path(directory)
    assert root.is_absolute()
    ancestors = []
    for path in [*reversed(root.parents), root]:
        info = path.lstat()
        assert stat.S_ISDIR(info.st_mode), ('project root ancestor is not a real directory', str(path))
        ancestors.append([str(path), 'directory', None])
    entries = []

    def visit(path, prefix=''):
        for name in sorted(os.listdir(path)):
            assert name.isascii(), ('unregistered non-ASCII project entry', str(path), name)
            child = path / name
            info = child.lstat()
            is_dir = stat.S_ISDIR(info.st_mode)
            is_link = stat.S_ISLNK(info.st_mode)
            candidate_file = name.endswith(('.py', '.pyc', '.so'))
            candidate_directory = name.isidentifier() and (is_dir or is_link)
            if not (candidate_file or candidate_directory):
                continue
            relative = prefix + name
            kind = ('symlink' if is_link else 'directory' if is_dir else
                    'file' if stat.S_ISREG(info.st_mode) else 'special')
            target = os.readlink(child) if is_link else None
            entries.append([relative, kind, target])
            assert kind not in ('symlink', 'special'), ('project candidate alias/special node forbidden', relative)
            if is_dir and name.isidentifier():
                visit(child, relative + '/')

    visit(root)
    entries.sort(key=lambda row: row[0])
    return {'schema': 'worker38-project-import-namespace-v2', 'root': str(root),
            'exists': True, 'root_type': 'directory', 'ancestor_entries': ancestors,
            'policy': PROJECT_NAMESPACE_POLICY, 'entries': entries,
            'entries_sha256': sha(canonical(entries))}


def elf(path):
    raw = Path(path).read_bytes()
    if not raw.startswith(b'\x7fELF'):
        return None
    assert raw[4:6] == b'\x02\x01', ('unsupported non-ELF64 little-endian', path)
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', raw)
    assert header[2] == 62, ('not x86_64', path)
    ph = [struct.unpack_from('<IIQQQQQQ', raw, header[5] + i * header[9]) for i in range(header[10])]
    dynamic = []
    for entry in ph:
        if entry[0] == 2:
            for offset in range(entry[2], entry[2] + entry[5], 16):
                tag, value = struct.unpack_from('<qQ', raw, offset)
                if tag == 0:
                    break
                dynamic.append((tag, value))
    strtabs = [value for tag, value in dynamic if tag == 5]
    base = None
    if strtabs:
        address = strtabs[0]
        base = next(entry[2] + address - entry[3] for entry in ph
                    if entry[0] == 1 and entry[3] <= address < entry[3] + entry[5])
    strings = {}
    for tag, label in ((1, 'needed'), (14, 'soname'), (15, 'rpath'), (29, 'runpath'),
                       (0x7fffffff, 'filter'), (0x7ffffffd, 'auxiliary')):
        strings[label] = [raw[base + value:raw.index(b'\0', base + value)].decode('ascii')
                          for found, value in dynamic if found == tag]
    strings['interpreter'] = [raw[entry[2]:entry[2] + entry[5]].rstrip(b'\0').decode('ascii')
                              for entry in ph if entry[0] == 3]
    return {'class': 'ELF64', 'endianness': 'little', 'machine': 'EM_X86_64', **strings}


cache_raw = Path('/etc/ld.so.cache').read_bytes()
assert cache_raw.startswith(b'glibc-ld.so.cache1.1')
cache_count, cache_strings_size = struct.unpack_from('<II', cache_raw, 20)
cache = {}
for index in range(cache_count):
    flags, key, value, osversion, hwcap = struct.unpack_from('<iIIIQ', cache_raw, 48 + index * 24)
    name = cache_raw[key:cache_raw.index(b'\0', key)].decode('ascii')
    path = cache_raw[value:cache_raw.index(b'\0', value)].decode('ascii')
    cache.setdefault(name, []).append({'path': path, 'flags': flags, 'osversion': osversion, 'hwcap': hwcap})

executables = ['/usr/bin/python3', '/usr/bin/python3.13', '/bin/bash', '/usr/bin/bash',
               '/usr/bin/timeout', '/usr/bin/env']
stdlib_inventory = inventory(STDLIB)
extension_paths = [str(path) for path in sorted((STDLIB / 'lib-dynload').glob('*.so'))]
queue = executables + extension_paths
elf_objects = {}
links = {}
missing = []
ambiguous = []
special_dynamic = []
while queue:
    requested = queue.pop(0)
    info = pin(requested)
    if not info['exists']:
        missing.append(requested)
        continue
    actual = str(Path(requested).resolve())
    if actual != requested:
        links[requested] = info
    if actual in elf_objects:
        continue
    metadata = elf(actual)
    if metadata is None:
        continue
    record = {'file': pin(actual), 'elf': metadata, 'dependency_resolution': []}
    elf_objects[actual] = record
    if any(metadata[key] for key in ('rpath', 'runpath', 'filter', 'auxiliary')):
        special_dynamic.append(actual)
    queue.extend(metadata['interpreter'])
    for name in metadata['needed']:
        candidates = cache.get(name, [])
        if '/' in name:
            candidates = [{'path': name, 'source': 'literal DT_NEEDED path'}]
        existing = [item for item in candidates if Path(item['path']).is_file()]
        resolved = sorted({str(Path(item['path']).resolve()) for item in existing})
        if not existing:
            missing.append({'object': actual, 'needed': name})
        if len(resolved) > 1:
            ambiguous.append({'object': actual, 'needed': name, 'resolved_candidates': resolved})
        record['dependency_resolution'].append({'needed': name, 'cache_candidates': candidates,
            'all_existing_resolved_candidates': resolved,
            'unique_current_object': len(resolved) == 1})
        queue.extend(item['path'] for item in existing)

site_roots = [Path('/usr/local/lib/python3.13/dist-packages'),
              Path('/usr/lib/python3/dist-packages'), Path('/usr/lib/python3.13/dist-packages')]
site_namespaces = [namespace(path) for path in site_roots]
pth = [pin(path) for root in site_roots if root.is_dir() for path in sorted(root.glob('*.pth'))]
site_source = Path('/usr/lib/python3.13/site.py').read_bytes()
site_tree = ast.parse(site_source)
site_spans = {}
for node in site_tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in (
        'addpackage', 'addsitedir', 'check_enableusersite', 'getsitepackages', 'venv',
        'execsitecustomize', 'execusercustomize', 'main'):
        raw = b''.join(site_source.splitlines(keepends=True)[node.lineno - 1:node.end_lineno])
        site_spans[node.name] = {'first_line': node.lineno, 'last_line': node.end_lineno, 'sha256': sha(raw)}

project_import_roots = [ROOT / 'evidence-design', ROOT / 'tests', ROOT / 'scripts']
search_roots = [STDLIB, STDLIB / 'lib-dynload'] + site_roots + project_import_roots
custom_candidates = {}
for module in ('sitecustomize', 'usercustomize', 'apport_python_hook'):
    rows = []
    for root in search_roots:
        if root.is_dir():
            rows.extend(pin(path) for path in sorted(root.iterdir())
                        if path.name == module or path.name.startswith(module + '.'))
    custom_candidates[module] = rows

absence_paths = ['/usr/bin/pyvenv.cfg', '/usr/pyvenv.cfg', '/usr/bin/python3._pth',
    '/usr/bin/python3.13._pth', '/usr/lib/python313.zip', '/usr/lib/python3.13.zip',
    '/etc/ld.so.preload', '/workspace/shared/.local/lib/python3.13/site-packages',
    '/usr/lib/x86_64-linux-gnu/glibc-hwcaps', '/usr/local/lib/glibc-hwcaps',
    '/usr/local/lib/x86_64-linux-gnu/glibc-hwcaps']
cached_headers = []
for path in sorted(STDLIB.rglob('*.pyc')):
    raw = path.read_bytes()
    assert len(raw) >= 16
    flags = struct.unpack_from('<I', raw, 4)[0]
    cached_headers.append([str(path.relative_to(STDLIB)), raw[:4].hex(), flags, raw[8:16].hex()])

source_names = sorted(set(['evidence-design/run-worker38-fixed-preparation.py',
    'evidence-design/assemble-worker38-prefix-map.py', LITERAL_RECIPE_SOURCE] +
    [str(path.relative_to(ROOT)) for path in (ROOT / 'scripts/worker38').glob('*.py')] +
    [str(path.relative_to(ROOT)) for path in (ROOT / 'tests').glob('*worker3[78]*.py')] +
    ['scripts/worker37_bootstrap.py', 'scripts/worker_bootstrap_shared.py']))
source_imports = {}
project_source_bytes = {}
project_source_asts = {}
for name in source_names:
    source_path = ROOT / name
    before = source_path.lstat()
    assert stat.S_ISREG(before.st_mode), ('project source is not a regular file', name)
    raw = source_path.read_bytes()
    after = source_path.lstat()
    assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), ('project source changed during its one read', name)
    assert len(raw) == before.st_size, ('project source byte length changed', name)
    tree = ast.parse(raw)
    project_source_bytes[name] = raw
    project_source_asts[name] = tree
    imports = sorted(set(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
                     | set(node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)))
    source_imports[name] = {'size_bytes': len(raw), 'sha256': sha(raw), 'syntactic_import_names': imports,
        'no_execution_claim': 'AST statement inventory includes conditional/unreachable imports; not an observed loaded-module list'}


def revalidate_first33_inputs():
    """Revalidate prospective attempt03 pins and their exact two-recipe delta."""
    current_artifact = ROOT / 'evidence-design/FIRST33-INDEPENDENT-INPUT-PINS.json'
    current_raw = current_artifact.read_bytes()
    baseline = json.loads(current_raw)
    assert sha(current_raw) == '1e20fef7dcd68026a6ed1c6c919132f56ccfcbe7a023c5c75676eb5b32d3f390'
    assert baseline['native_output_root'] == '/workspace/shared/worker38-native-batch-03'
    preserved = Path('/workspace/shared/worker38-native-attempt02-repair01-candidate')
    original = preserved / 'evidence-design/FIRST33-INDEPENDENT-INPUT-PINS.json'
    original_raw = original.read_bytes()
    assert sha(original_raw) == '88c57140eb8a559b48928684d5aa8807454f5ce1ee2977167b709ebe8391560c'
    prior = json.loads(original_raw)
    assert set(prior['recipes']) == set(baseline['recipes'])
    changed_recipe_ids = [key for key, value in baseline['recipes'].items()
        if (value['size_bytes'], value['sha256']) != (
            prior['recipes'][key]['size_bytes'], prior['recipes'][key]['sha256'])]
    assert set(changed_recipe_ids) == {'copy:scripts/worker38-bootstrap.sh', 'S09-symlink-target'}
    paths = ['tests/test_worker38_bootstrap_integration.py',
             'tests/test_worker37_bootstrap.py', 'tests/worker38_literal_fixtures.py']
    old_asts = {name: ast.parse((preserved / name).read_bytes()) for name in paths}

    def function(tree, name):
        nodes = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name]
        assert len(nodes) == 1, name
        return nodes[0]

    def literal(name, key):
        nodes = [node for node in project_source_asts[name].body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == key for target in node.targets)]
        assert len(nodes) == 1 and isinstance(nodes[0].value, ast.Constant), (name, key)
        return ast.literal_eval(nodes[0].value)

    def dump(node):
        return ast.dump(node, include_attributes=False)

    def setup_prefix(name, key, marker):
        node = function(project_source_asts[name], key)
        old = function(old_asts[name], key)
        def extract(fn):
            body = fn.body
            if key == 'run_bash':
                assert isinstance(body[0], ast.With)
                body = body[0].body
            result = []
            for item in body:
                result.append(item)
                calls = [child for child in ast.walk(item) if isinstance(child, ast.Call)]
                if any((isinstance(call.func, ast.Name) and call.func.id == marker) or
                       (isinstance(call.func, ast.Attribute) and call.func.attr == marker) for call in calls):
                    return result
            raise AssertionError(('setup boundary absent', name, key))
        current, historical = extract(node), extract(old)
        current_dump = [dump(item) for item in current]
        historical_dump = [dump(item) for item in historical]
        writers = lambda body: [dump(child) for item in body for child in ast.walk(item)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
            and child.func.attr in ('write_bytes', 'write_text', 'symlink_to')]
        current_writers, historical_writers = writers(current), writers(historical)
        assert current_writers == historical_writers, ('setup byte-writer AST changed', name, key)
        return {'path': name, 'helper': key, 'boundary': marker,
            'whole_setup_prefix_AST_unchanged': current_dump == historical_dump,
            'setup_byte_writer_ASTs_unchanged': True, 'writer_count': len(current_writers),
            'current_setup_prefix_AST_sha256': sha(canonical(current_dump)),
            'historical_setup_prefix_AST_sha256': sha(canonical(historical_dump))}

    checks = [setup_prefix(paths[0], 'pipeline', 'watch_production'),
              setup_prefix(paths[0], 'bash_case', 'watch_production'),
              setup_prefix(paths[1], 'run_bash', '_watch_production')]
    set_up_equal = dump(function(project_source_asts[paths[0]], 'setUp')) == dump(function(old_asts[paths[0]], 'setUp'))
    assert set_up_equal, 'first33 setup function changed'
    methods = []
    for row in baseline['cases']:
        method = row['selector'].rsplit('.', 1)[-1]
        equal = dump(function(project_source_asts[paths[0]], method)) == dump(function(old_asts[paths[0]], method))
        assert equal, ('registered first33 method AST changed', method)
        methods.append({'id': row['id'], 'selector': row['selector'], 'AST_unchanged': True})

    checks_by_recipe = {}
    additional_copied_source_pins = {}
    for key, recipe in baseline['recipes'].items():
        if key.startswith('copy:'):
            name = key[5:]
            if name in source_imports:
                size, digest = source_imports[name]['size_bytes'], source_imports[name]['sha256']
            else:
                path = ROOT / name
                before = path.lstat()
                assert stat.S_ISREG(before.st_mode)
                raw = path.read_bytes()
                after = path.lstat()
                assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (
                    after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                size, digest = len(raw), sha(raw)
                additional_copied_source_pins[name] = {'size_bytes': size, 'sha256': digest}
        elif key in ('BASH_STUB', 'FROZEN_STUB'):
            raw = literal(paths[0] if key == 'BASH_STUB' else paths[1], key).encode('utf-8')
            size, digest = len(raw), sha(raw)
        elif key == 'invented-credential':
            raw = literal(paths[2], 'CREDENTIAL').encode('utf-8')
            size, digest = len(raw), sha(raw)
        elif key == 'consumed-reservation':
            head = literal(paths[2], 'HEAD')
            allocation = literal('scripts/worker38/admission.py', 'ALLOCATION')
            raw = ('schema=worker38-observed-reservation-v1\nallocation_id=' + allocation +
                '\nrun_id=501\nrun_attempt=1\nobserved_head=' + head +
                '\ndescriptor_binding=not_yet_validated\nevaluator_starts=0\nscientific_classification=null\n').encode('ascii')
            size, digest = len(raw), sha(raw)
        elif key == 'S09-symlink-target':
            raw = b'/workspace/shared/worker38-native-batch-03/c0009/t01/actual'
            size, digest = len(raw), sha(raw)
        else:
            raw = bytes.fromhex(recipe['complete_bytes_hex'])
            names = [paths[1]] if key == 'legacy-library' else [paths[0]]
            for name in names:
                values = [node.args[0].value for node in ast.walk(function(project_source_asts[name],
                    'run_bash' if name == paths[1] else 'bash_case'))
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'write_bytes' and node.args and isinstance(node.args[0], ast.Constant)]
                assert raw in values, ('setup literal absent', key)
            size, digest = len(raw), sha(raw)
        assert (size, digest) == (recipe['size_bytes'], recipe['sha256']), ('prospective input byte recipe differs', key)
        checks_by_recipe[key] = {'size_bytes': size, 'sha256': digest,
            'matches_current_attempt03_input_pin': True,
            'matches_preserved_attempt02_byte_recipe': key not in changed_recipe_ids,
            'preserved_attempt02_size_bytes': prior['recipes'][key]['size_bytes'],
            'preserved_attempt02_sha256': prior['recipes'][key]['sha256']}
    return {'status': 'ALL16_ATTEMPT03_PINS_MATCH; EXACTLY2_AUTHORIZED_BYTE_RECIPES_CHANGED; ALL33_METHOD_ASTS_UNCHANGED',
        'current_artifact': {'path': str(current_artifact.relative_to(ROOT)), 'size_bytes': len(current_raw),
            'sha256': sha(current_raw), 'native_output_root': baseline['native_output_root']},
        'original_artifact': {'path': str(original), 'size_bytes': len(original_raw),
            'sha256': sha(original_raw), 'unchanged': True},
        'old_source_pin_role': 'The preserved attempt02 artifact and its whole-source/helper hashes are historical provenance. The current attempt03 artifact independently pins the guarded post-cd OLDPWD-unset wrapper and output03 S09 bytes, not observed producer outputs. BASH_STUB is unchanged. Current source authority is the revised map and this inventory.',
        'preserved_review_handoff_sha256': '931e661773ea71ac2669028be7da049b5e09aad69478d428747dd678d6c4c344',
        'parent_selected_scope': baseline['attempt03_lineage']['parent_selected_scope'],
        'attempt02_closure_comment': 5994611617,
        'changed_recipe_ids': sorted(changed_recipe_ids), 'unchanged_recipe_count': 14,
        'attempt03_input_delta': baseline['attempt03_lineage'],
        'setUp_AST_unchanged': set_up_equal, 'setup_prefix_checks': checks,
        'methods': methods, 'recipe_checks': checks_by_recipe,
        'additional_copied_source_pins': additional_copied_source_pins,
        'interpretation': 'Only AST/data/byte hashing occurred. No test helper executed and no producer result was generated or promoted to an input.'}


# The routine above remains exact historical attempt03 proof source. It is not
# the attempt04 input gate: calling it here would couple environmental evidence
# to old literal pins and create a cycle with the new full397 materialization.
historical_first33_artifact = pin(ROOT / 'evidence-design/FIRST33-INDEPENDENT-INPUT-PINS.json')
assert historical_first33_artifact['sha256'] == '1e20fef7dcd68026a6ed1c6c919132f56ccfcbe7a023c5c75676eb5b32d3f390'
historical_first33_record = {
    'status': 'HISTORICAL_ATTEMPT03_INPUT_ARTIFACT_ONLY',
    'artifact': historical_first33_artifact,
    'native_output_root': '/workspace/shared/worker38-native-batch-03',
    'current_literal_input_admission': False,
    'interpretation': 'Exact retained old artifact identity only; the historical revalidation routine was not called. Current full397 literal identities require their separate independent materialization and final map gate.'}

config_paths = ['/etc/ld.so.cache', '/etc/ld.so.conf', '/etc/ld.so.conf.d/libc.conf',
    '/etc/ld.so.conf.d/x86_64-linux-gnu.conf', '/usr/lib/ssl/openssl.cnf', '/etc/ssl/openssl.cnf',
    '/usr/lib/ssl/cert.pem', '/usr/lib/ssl/certs', '/etc/nsswitch.conf', '/etc/passwd',
    '/etc/group', '/etc/localtime', '/usr/share/zoneinfo/Asia/Jerusalem',
    '/etc/python3.13/sitecustomize.py']
report = {
    'schema': 'worker38-static-native-environment-closure-v1',
    'status': 'STATIC_FILE_AND_DT_NEEDED_PINS_COMPLETE_WITH_EXPLICIT_NONEXECUTION_LIMITS',
    'activity': {'project_imports': 0, 'test_imports': 0, 'fixture_calls': 0,
        'target_interpreter_invocations': 0, 'target_Bash_invocations': 0, 'target_timeout_invocations': 0,
        'runtime_probes': 0, 'process_probes': 0, 'network_probes': 0, 'bytecode_execution': 0,
        'operation': 'Read paths/file bytes; AST parse; SHA256; static ELF64 and loader-cache parsing; write only this metadata JSON'},
    'deriver': {'path': str(Path(__file__).relative_to(ROOT)), 'sha256': sha(Path(__file__).read_bytes())},
    'planned_owner_environment': {'PATH': '/usr/bin:/bin', 'HOME': '/workspace/shared', 'TMPDIR': '/workspace/shared',
        'LC_ALL': 'C', 'LANG': 'C', 'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'},
    'external_map_gate_variable': 'WORKER38_FIXED_MAP_SHA256 must separately equal the exact root-approved map SHA256',
    'positive_environment_requirements': [
        'Construct the explicit clean child environment from this allowlist, rather than updating inherited os.environ. The managed exec shell is trusted platform outside the candidate proof; no pre-shell allowlist enforcement is claimed.',
        'All LD_* and PYTHON* names absent except the three explicit Python allowlist names; especially LD_PRELOAD, LD_LIBRARY_PATH, LD_AUDIT, PYTHONPATH, PYTHONHOME, PYTHONSTARTUP, PYTHONPYCACHEPREFIX absent.',
        'COLOREDLOGS_AUTO_INSTALL, BASH_ENV, ENV, SHELLOPTS, BASHOPTS, GLIBC_TUNABLES, LOCPATH, GCONV_PATH, SSL_CERT_FILE, SSL_CERT_DIR, OPENSSL_CONF, OPENSSL_MODULES, OPENSSL_ENGINES and TZ are absent.',
        'Keep the existing 25 registered literal Bash invocation templates and shebangs unchanged. The separately selected names-only diagnostic changes its pinned inert stub bytes, not the process roster; this report authorizes no extra children.',
        'Native scratch stubs and project/test source inputs are independently pinned in the fixed map; this manifest never treats their output as environmental input.'],
    'launch_contract': {'interpreter': '/usr/bin/python3', 'interpreter_resolves_to': '/usr/bin/python3.13',
        'python_flags': ['-B', '-P'], 'safe_path': True,
        'outer_timeout': '/usr/bin/timeout --signal=KILL 600s',
        'Bash': '/bin/bash', 'version_labels_are_filename_and_source_inferences': True,
        'verified_runtime_version': None, 'executables': [pin(path) for path in executables]},
    'trust_boundaries': {
        'managed_exec_shell': 'Trusted platform outside candidate proof; inherited startup behavior before the explicit clean child is not claimed to be prevented by an in-shell unset or env command.',
        'explicit_clean_child': 'The fixed positive environment and inherited resource limits apply from the explicitly clean child onward, before its timeout/Python exec. Exact command/source review must establish this boundary.',
        'initial_Python_startup': 'Pinned native interpreter, stdlib/site/source/cache inputs are trusted runtime inputs. Native-only -P prevents prepending the script directory/current directory; PYTHONPATH is absent. Verification inside the runner cannot retroactively prevent its initial imports; source/cache semantic equivalence remains unproved.',
        'project_imports': 'Require sys.flags.safe_path=true and check exact recursive v2 project candidate namespaces plus map source pins before explicitly inserting project/test paths or performing lazy project/test imports. This is an enforced pre-project condition, distinct from trusted interpreter startup.',
        'external_600_seconds': 'GNU timeout hard600 interval starts at the actual timeout invocation. Any earlier BOOTTIME sample/cutoff is a conservative cooperative deadline; it is not claimed to start the later external timer.',
        'no_authority': 'These are explicit root-supplied trust/interval definitions for revised static review, not a native execution gate.'},
    'path_aliases': [pin(path) for path in ('/bin', '/lib', '/lib64', '/usr/lib64/ld-linux-x86-64.so.2')],
    'stdlib_complete_tree': stdlib_inventory,
    'cached_bytecode': {'count': len(cached_headers),
        'all_bytes_pinned_by_stdlib_tree': True, 'header_columns': ['relative_path', 'magic_hex', 'flags', 'validation_payload_hex'],
        'headers': cached_headers, 'headers_sha256': sha(canonical(cached_headers)),
        'semantics': '-B and PYTHONDONTWRITEBYTECODE prevent new .pyc writes, not reads. Existing .pyc bytes and source mtime_ns are bound. No cache was deleted, generated, loaded or unmarshalled.',
        'limit': 'Matching .pyc/source freshness fields do not independently prove equivalent code. This report pins both; no source-equivalence claim is made.'},
    'site': {'source': pin('/usr/lib/python3.13/site.py'), 'source_function_spans': site_spans,
        'global_site_directory_namespaces': site_namespaces, 'pth_files': pth,
        'coloredlogs_condition': 'The only observed .pth imports os and executes a fixed try expression. __import__(coloredlogs).auto_install() occurs only if COLOREDLOGS_AUTO_INSTALL is truthy; it is absent in the positive environment.',
        'customizer_candidates': custom_candidates,
        'sitecustomize_source_semantics': 'Source attempts apport_python_hook import and catches ImportError; no matching candidate exists in the enumerated startup import roots. Cached bytecode is separately pinned, not proven equivalent.',
        'user_site': 'PYTHONNOUSERSITE=1 makes site.check_enableusersite return False; user-site addition and usercustomize import are skipped by the pinned site.main source.',
        'site_packages_scope': 'Immediate namespace membership plus every .pth/customizer candidate is pinned. Unreachable third-party package contents are not claimed as a closed import graph.'},
    'absent_or_present_startup_candidates': [pin(path) for path in absence_paths],
    'loader_cache': {'header_format': 'glibc-ld.so.cache1.1, 48-byte header and 24-byte entries',
        'entry_count': cache_count, 'string_table_bytes': cache_strings_size, 'file': pin('/etc/ld.so.cache')},
    'elf_closure': {'roots': executables + extension_paths, 'objects': elf_objects,
        'symlink_requests': links, 'object_count': len(elf_objects),
        'missing_DT_NEEDED_candidates': missing, 'multiple_distinct_cache_candidates': ambiguous,
        'RPATH_RUNPATH_FILTER_AUXILIARY_objects': special_dynamic,
        'scope': 'Full static DT_NEEDED transitive closure of owner executables and every current stdlib lib-dynload extension; exact loader/cache/config bytes pinned. This overbounds extensions selected by actual admitted imports.',
        'resolution_limit': 'No loader or ldd was run. Unique cache object claims are static, conditional on absent loader environment/preload and unchanged cache/path aliases. Arbitrary future dlopen names are not inferred.'},
    'configuration_files': [pin(path) for path in config_paths],
    'SSL_default_certificate_tree': inventory('/etc/ssl/certs'),
    'SSL_reason': 'Worker38 admission.Client constructs ssl.create_default_context even when HTTP responses are mocked; OpenSSL config/default CA bytes are environmental inputs.',
    'timezone': {'TZ_environment': 'absent', 'observed_localtime_target': '/usr/share/zoneinfo/Asia/Jerusalem',
        'effect': 'Local timezone conversions may use this pinned zone. No timezone setting was changed; this is not a claim about the user timezone.'},
    'project_syntactic_import_inventory': source_imports,
    'project_import_roots': [project_namespace(path) for path in project_import_roots],
    'historical_first33_input_recipe_record': historical_first33_record,
    'source_input_binding': {
        'schema': 'worker38-preparation-source-input-binding-v1',
        'native_output_root': NATIVE_OUTPUT_ROOT,
        'recipe_source': LITERAL_RECIPE_SOURCE,
        'recipe_source_identity': source_imports[LITERAL_RECIPE_SOURCE],
        'literal_input_materialization': 'SEPARATE_FULL397_MATERIALIZATION_REQUIRED',
        'current_literal_input_admission': False},
    'remaining_uncertainties': [
        'Actual CPython sys.path, loaded modules, built-in/frozen tables and runtime version have not been probed. Interpreter bytes bind their implementation; runtime equivalence to source directories is conditional on the fixed command/env and unchanged path layout.',
        'Cached .pyc/source semantic equivalence was not proved; both byte sets and freshness metadata are pinned as trusted initial-runtime inputs, not executable proof of equivalence.',
        'AST imports do not prove a complete dynamic import graph. The registered no-historical-import guard and separately reviewed source graph remain required.',
        'Static DT_NEEDED closure does not enumerate every optional dlopen/configuration branch of all overbounded unused extensions.',
        'Kernel/CPU/auxv/VDSO, inherited runtime state, descriptor limits, clocks, PID allocation and procfs observations are not frozen by a file manifest. Any required observations must remain within the separately admitted native batch, never standalone probes.',
        'No executable or source under inspection was run, so this manifest is static review evidence and grants no execution authority.'],
    'preentry_requirements': [
        'Within the bounded clean child, recheck the pinned runtime files, cache/source freshness, aliases, namespace membership and absence assertions before lazy project imports. This cannot validate imports already performed during trusted interpreter startup retroactively.',
        'Require native-only -B -P and sys.flags.safe_path=true; enforce recursive project v2 schema, exact ancestor/entry rows, no-symlink/no-special policy, and entries digest before inserting project paths or lazy project/test imports. Fail closed on absent roots, new candidates, types, aliases or caches. Scientific -B -s settings are unchanged.',
        'Construct the positive environment before the explicit clean child startup and enforce its resource limits; the managed exec shell is separately trusted platform and is outside this candidate proof.',
        'Resolve all reported missing dependencies, ambiguous bindings or unexpected dynamic tags before claiming a unique native loader closure.',
        'Root must explicitly accept the pinned source/cache semantics and remaining nonexecution limits as sufficient, or keep the native gate held.'],
}
# Exact original serialization, including LF, bounded before any output open.
# Exit 73 is reserved solely for this positively established encoded-byte cap.
_encoded_report = (json.dumps(report, sort_keys=True, separators=(',', ':')) + '\n').encode('ascii')
if len(_encoded_report) > 8388608:
    raise SystemExit(73)
_output_failure = None
_output_parent_fd = None
_output_fd = None
try:
    _output_parent_fd = os.open(OUT.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    _output_fd = os.open(OUT.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                         0o600, dir_fd=_output_parent_fd)
    # One unbuffered write: no user-space buffer or close-time flush retry.
    _written = os.write(_output_fd, _encoded_report)
    if type(_written) is not int or _written != len(_encoded_report):
        raise OSError('incomplete exclusive environment output write')
except BaseException as _failure:
    _output_failure = _failure
finally:
    # Persist complete or partial bytes and their directory entry once. Any
    # secondary failure is chained under the first; it cannot replace it.
    for _owned_fd in (_output_fd, _output_parent_fd):
        if _owned_fd is None:
            continue
        try:
            os.fsync(_owned_fd)
        except BaseException as _failure:
            if _output_failure is None:
                _output_failure = _failure
            else:
                _failure.__context__ = _output_failure.__cause__
                _output_failure.__cause__ = _failure
        try:
            os.close(_owned_fd)
        except BaseException as _failure:
            if _output_failure is None:
                _output_failure = _failure
            else:
                _failure.__context__ = _output_failure.__cause__
                _output_failure.__cause__ = _failure
if _output_failure is not None:
    raise _output_failure
print(json.dumps({'path': str(OUT), 'size_bytes': OUT.stat().st_size, 'sha256': sha(OUT.read_bytes()),
    'stdlib_entries': stdlib_inventory['entry_count'], 'cached_pyc': len(cached_headers),
    'elf_objects': len(elf_objects), 'missing_needed': missing, 'ambiguous_cache_bindings': len(ambiguous),
    'special_dynamic_objects': special_dynamic, 'pth_files': [item['path'] for item in pth]}, sort_keys=True))
