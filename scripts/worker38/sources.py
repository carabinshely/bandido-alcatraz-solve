"""Exact historical bytes, static closure checks and isolated imports."""
from __future__ import annotations
import ast
import hashlib
import importlib
from pathlib import Path
import sys
import sysconfig
from .common import HISTORICAL, REPOSITORY, canonical, file_info, require, sha, strict_json, SOURCE_MANIFEST_SHA256


def verify_blob(raw, entry):
    require(len(raw) == entry['size_bytes'] and sha(raw) == entry['sha256'],
            'historical raw byte hash mismatch: ' + entry['path'])
    require(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == entry['git_blob'],
            'historical Git blob identity mismatch: ' + entry['path'])


def read_manifest(path):
    raw = Path(path).read_bytes()
    require(len(raw) <= 2 * 1024 ** 2 and sha(raw) == SOURCE_MANIFEST_SHA256, 'exact comparator manifest bytes required')
    value = strict_json(raw)
    require(value['schema'] == 'worker38-comparator-closure-v1' and value['historical_commit'] == HISTORICAL
            and value['repository'] == REPOSITORY, 'historical source manifest identity')
    seen = set()
    for entry in value['files']:
        p = Path(entry['path'])
        require(not p.is_absolute() and '..' not in p.parts and entry['path'] not in seen
                and p.suffix == '.py' and p.parts[0] in ('src', 'scripts'), 'invalid source path')
        seen.add(entry['path'])
    require(len(value['files']) == 21 and len({x['module'] for x in value['files']}) == len(seen), 'duplicate source module')
    return value


def restore_staged(repo, target, manifest, budget):
    """Copy the exact inert .blob closure; no Git history or network fetch."""
    target = Path(target)
    require(not target.exists(), 'exclusive restored source directory required')
    staging = Path(repo) / 'experiments/worker38-synthetic-profile/inputs/comparator-7ac2f62c'
    require(staging.is_dir() and not staging.is_symlink(), 'fixed inert source staging directory required')
    expected = {entry['path'] + '.blob' for entry in manifest['files']}
    actual = set()
    for path in staging.rglob('*'):
        require(not path.is_symlink(), 'symlink in inert source closure')
        if path.is_file(): actual.add(path.relative_to(staging).as_posix())
        else: require(path.is_dir(), 'special file in inert source closure')
    require(actual == expected and len(expected) == 21, 'exact inert21-file source closure required')
    budget.mkdir(target)
    for entry in manifest['files']:
        path = staging / (entry['path'] + '.blob')
        require(path.is_file() and path.stat().st_size == entry['size_bytes'], 'staged source size')
        raw = path.read_bytes()
        verify_blob(raw, entry)
        budget.write(target / entry['path'], raw, raw=True)
    verify_files(target, manifest)


def restore(repo, target, manifest, budget):
    """Fixed compatibility name for the same inert source-copy implementation."""
    return restore_staged(repo, target, manifest, budget)


def verify_files(root, manifest):
    root = Path(root).resolve()
    expected = {x['path'] for x in manifest['files']}
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    require(actual == expected, 'unexpected or missing restored source file')
    for e in manifest['files']:
        p = root / e['path']
        require(not p.is_symlink() and p.resolve().is_relative_to(root), 'unsafe restored source path')
        verify_blob(p.read_bytes(), e)


def isolated_imports(root, manifest):
    """Install frozen paths and CPython library paths only; reject preloaded science."""
    root = Path(root).resolve()
    names = {e['module'] for e in manifest['files']}
    require(not any(n in sys.modules for n in names), 'ambient historical source module')
    stdlib = Path(sysconfig.get_path('stdlib')).resolve()
    keep = []
    for item in sys.path:
        if not item:
            continue
        p = Path(item).resolve()
        if 'site-packages' in p.parts or 'dist-packages' in p.parts:
            continue
        if p == stdlib or p.is_relative_to(stdlib) or p == stdlib.parent / 'python311.zip':
            keep.append(str(p))
    require(str(stdlib) in keep, 'CPython stdlib import path missing')
    sys.path[:] = [str(root / 'scripts'), str(root / 'src'), *keep]
    # Main package was imported before narrowing sys.path. No new driver package
    # discovery depends on the checkout after this point.
    modules = {name: importlib.import_module(name) for name in (
        'worker35_resources', 'run_quota_reserve_closure_development',
        'benchmark_worker35_synthetic', 'bandido_alcatraz.quota_reserve_closure',
        'bandido_alcatraz.quota_reserve_closure_reference', 'bandido_alcatraz.worker32.evidence')}
    verify_modules(root, manifest)
    return modules


def verify_modules(root, manifest):
    root = Path(root).resolve(); pins = {e['module']: e for e in manifest['files']}
    observed = {}
    for name, module in tuple(sys.modules.items()):
        if name.startswith('bandido_alcatraz') or name in pins:
            require(name in pins, 'unmanifested scientific module: ' + name)
            e = pins[name]
            path = Path(module.__file__).resolve()
            require(path == root / e['path'], 'scientific module origin drift: ' + name)
            verify_blob(path.read_bytes(), e)
            observed[name] = {'path': str(path), **file_info(path), 'git_blob': e['git_blob']}
    return observed


def fixture_ast(source):
    """Select unchanged invented constructor statements without running main."""
    tree = ast.parse(source)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    loop = next(n for n in main.body if isinstance(n, ast.For) and isinstance(n.target, ast.Name)
                and n.target.id == 'n')
    prefix = []
    for node in main.body:
        if isinstance(node, ast.ImportFrom) and node.module in (
            'bandido_alcatraz.board', 'bandido_alcatraz.game', 'bandido_alcatraz.model',
            'bandido_alcatraz.setup'):
            prefix.append(node)
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Tuple) and
                [x.id for x in t.elts] == ['N', 'E', 'S', 'W'] for t in node.targets):
            prefix.append(node)
        if isinstance(node, ast.FunctionDef) and node.name == 'card':
            prefix.append(node)
    body = []
    for node in loop.body:
        body.append(node)
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'public'
                                               for t in node.targets):
            break
    require(len(prefix) == 6 and len(body) == 13, 'frozen constructor shape changed')
    return prefix + body


def construct_fixture(size, restored):
    # This function is reachable only in the admitted cell, never in source
    # verification or tests. Nodes retain original values/order/semantics.
    source = (Path(restored) / 'scripts/benchmark_worker35_synthetic.py').read_bytes()
    nodes = fixture_ast(source)
    manifest = read_manifest(Path(restored).parent / 'source-manifest.json')
    verify_constructor(source, manifest['constructor'])
    code = compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
                   str(Path(restored) / 'scripts/benchmark_worker35_synthetic.py'), 'exec')
    namespace = {'n': size}
    exec(code, namespace)
    return namespace['state'], namespace['catalog'], namespace['inputs'], namespace['public']



CONSTRUCTOR_AST_SCHEMA = 'worker36-constructor-ast-v1'
# Explicit semantic shape of the selected frozen constructor, independent of
# CPython's ast.dump formatting and its 3.12 empty type_params addition.
CONSTRUCTOR_AST_FIELDS = {
    'Add': (),
    'Assign': ('targets', 'value', 'type_comment'),
    'Attribute': ('value', 'attr', 'ctx'),
    'BinOp': ('left', 'op', 'right'),
    'Call': ('func', 'args', 'keywords'),
    'Compare': ('left', 'ops', 'comparators'),
    'Constant': ('value', 'kind'),
    'Dict': ('keys', 'values'),
    'Expr': ('value',),
    'For': ('target', 'iter', 'body', 'orelse', 'type_comment'),
    'FormattedValue': ('value', 'conversion', 'format_spec'),
    'FunctionDef': ('name', 'args', 'body', 'decorator_list', 'returns', 'type_comment'),
    'IfExp': ('test', 'body', 'orelse'),
    'ImportFrom': ('module', 'names', 'level'),
    'JoinedStr': ('values',),
    'List': ('elts', 'ctx'),
    'ListComp': ('elt', 'generators'),
    'Load': (),
    'Lt': (),
    'Name': ('id', 'ctx'),
    'NotIn': (),
    'Return': ('value',),
    'SetComp': ('elt', 'generators'),
    'Slice': ('lower', 'upper', 'step'),
    'Store': (),
    'Subscript': ('value', 'slice', 'ctx'),
    'Tuple': ('elts', 'ctx'),
    'alias': ('name', 'asname'),
    'arg': ('arg', 'annotation', 'type_comment'),
    'arguments': ('posonlyargs', 'args', 'vararg', 'kwonlyargs', 'kw_defaults', 'kwarg', 'defaults'),
    'comprehension': ('target', 'iter', 'ifs', 'is_async'),
    'keyword': ('arg', 'value'),
}


def constructor_ast_bytes(node):
    """Canonical inert AST evidence; never normalize or mutate executable nodes."""
    locations = {'lineno', 'col_offset', 'end_lineno', 'end_col_offset'}
    def encode(value):
        if isinstance(value, ast.AST):
            name = type(value).__name__
            require(name in CONSTRUCTOR_AST_FIELDS and type(value) is getattr(ast, name),
                    'unexpected constructor AST node: ' + name)
            fields = CONSTRUCTOR_AST_FIELDS[name]
            accepted = (fields, fields + ('type_params',)) if name == 'FunctionDef' else (fields,)
            require(type(value._fields) is tuple and value._fields in accepted,
                    'unexpected constructor AST fields: ' + name)
            require(set(value._attributes) <= locations, 'unexpected constructor AST attributes: ' + name)
            allowed = set(fields) | locations | {'_fields'}
            if name == 'FunctionDef':
                allowed.add('type_params')
                if hasattr(value, 'type_params'):
                    require(type(value.type_params) is list and not value.type_params,
                            'constructor type parameters must be absent or empty')
            require(set(vars(value)) <= allowed, 'unexpected constructor AST semantic attribute: ' + name)
            require(all(hasattr(value, field) for field in fields),
                    'missing constructor AST semantic field: ' + name)
            return {'node': name, 'fields': [[field, encode(getattr(value, field))] for field in fields]}
        if type(value) is list:
            return [encode(item) for item in value]
        require(value is None or type(value) in (bool, int, str), 'unexpected constructor AST scalar')
        return value
    require(isinstance(node, ast.AST), 'constructor AST node required')
    return canonical({'schema': CONSTRUCTOR_AST_SCHEMA, 'tree': encode(node)})


def verify_constructor(source, expected):
    require(expected.get('ast_canonical_schema') == CONSTRUCTOR_AST_SCHEMA,
            'constructor AST canonical schema mismatch')
    nodes = fixture_ast(source); lines = source.splitlines(keepends=True)
    observed = [{'first_line': n.lineno, 'last_line': n.end_lineno,
                 'raw_span_sha256': sha(b''.join(lines[n.lineno - 1:n.end_lineno])),
                 'ast_sha256': sha(constructor_ast_bytes(n))} for n in nodes]
    require(observed == expected['selected_nodes'], 'frozen constructor source spans/bindings drift')
    return observed
