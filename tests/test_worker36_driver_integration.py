"""D01–D54 and fixed recovery R1D01–R1D16; no historical policy execution."""
from contextlib import ExitStack
import copy
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from worker36 import common as c, driver as d
from worker36 import supervision as supervision
from worker36 import verify as verification, transport

STUB_SUPERVISOR_INVOCATIONS = 0
FAKE_CELL = {'cell': 1, 'condition': 'U', 'size': 'fixed-literal-orchestration-stub', 'repetition': 1}
LITERAL_LOADER_PIN = {'schema': 'worker36-loader-pin-v1',
    'executable_sha256': 'a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc',
    'library_relative_path': 'Python/3.11.16/x64/lib/libpython3.11.so.1.0',
    'library_sha256': '4' * 64, 'library_size_bytes': 4096}
LITERAL_BOOT_ID = '11111111-2222-3333-4444-555555555555'
RESTORATION_CASES = ('disable_before', 'handler_before', 'disable_after_memory',
    'handler_after_memory', 'disable_mismatch', 'handler_mismatch',
    'disable_getter', 'handler_getter')


def literal_loader_identity():
    cache = '/literal-runner/tool-cache'
    library = cache + '/' + LITERAL_LOADER_PIN['library_relative_path']
    directory = library.rsplit('/', 1)[0]
    return {**copy.deepcopy(LITERAL_LOADER_PIN), 'schema': 'worker36-loader-identity-v1',
        'tool_cache': cache, 'executable_path': cache + '/Python/3.11.16/x64/bin/python3.11',
        'library_path': library, 'library_directory': directory,
        'library_device': {'major': 8, 'minor': 1}, 'library_inode': 101,
        'mapped_library': {'path': library, 'device': {'major': 8, 'minor': 1}, 'inode': 101},
        'loader_environment': {'LD_LIBRARY_PATH': directory}}


class LiteralTimers:
    """Literal timer and handler state only; no OS timer is ever installed."""
    def __init__(self, now):
        self.now = now
        self.old = object()
        self.handler = self.old
        self.timer = (0.0, 0.0)
        self.events = []
        self.restoring = False
        self.case = None

    def setitimer(self, which, seconds, interval=0):
        self.events.append(('timer', self.now(), seconds))
        prior = self.timer
        if seconds == 0:
            self.restoring = True
            if self.case == 'disable_before': raise OSError('literal disable failed before operation')
            if self.case != 'disable_mismatch': self.timer = (0.0, 0.0)
            if self.case == 'disable_after_memory': raise MemoryError('literal disable confirmed after allocation failure')
        else:
            self.timer = (seconds, interval)
        return prior

    def signal(self, number, handler):
        self.events.append(('handler', self.now(), handler is self.old))
        prior = self.handler
        if handler is self.old and self.case == 'handler_before':
            raise OSError('literal handler failed before operation')
        if not (handler is self.old and self.case == 'handler_mismatch'):
            self.handler = handler
        if handler is self.old and self.case == 'handler_after_memory':
            raise MemoryError('literal handler confirmed after allocation failure')
        return prior

    def getitimer(self, which):
        self.events.append(('get_timer', self.now()))
        if self.restoring and self.case == 'disable_getter': raise OSError('literal timer getter unavailable')
        return self.timer

    def getsignal(self, number):
        self.events.append(('get_handler', self.now()))
        if self.restoring and self.case == 'handler_getter': raise OSError('literal handler getter unavailable')
        return self.handler

class DriverIntegration(unittest.TestCase):
    def setUp(self):
        self.now = 1000.0
        self.ns = 1000000000000
        self.timers = LiteralTimers(lambda: self.now)
        literal = ExitStack(); self.addCleanup(literal.close)
        literal.enter_context(patch.object(time, 'monotonic', side_effect=lambda: self.now))
        literal.enter_context(patch.object(time, 'monotonic_ns', side_effect=self.next_ns))
        literal.enter_context(patch.object(time, 'process_time', return_value=0.0))
        literal.enter_context(patch.object(time, 'clock_gettime', side_effect=lambda clock: self.now))
        literal.enter_context(patch.object(supervision, '_usage', return_value=0.0))
        for name in ('signal', 'setitimer', 'getsignal', 'getitimer'):
            literal.enter_context(patch.object(d.signal, name, side_effect=getattr(self.timers, name)))
        literal.enter_context(patch.object(c, 'loader_identity', side_effect=literal_loader_identity))
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.attempt = self.root/'attempt'; self.auth = self.root/'auth'; self.auth.mkdir()
        self.claim = self.root/'claims'; self.claim.mkdir()
        self.experiment = self.root/'experiment'; self.experiment.mkdir()
        (self.experiment/'source-manifest.json').write_bytes(c.canonical({'files':[]}))
        self.test_receipt = self.root/'stub-test-receipt.json'; self.test_receipt.write_bytes(c.canonical({'literal':'stub'}))
        self.admission=self.auth/'admission.json';self.admission.write_bytes(c.canonical({'literal':'GO stub'}))
        self.provenance=self.auth/'provenance.json';self.provenance.write_bytes(c.canonical({'literal':'provenance stub'}))
        for name in ('event.json','pull-request.json','postmerge-ci.json','request-context.json'):
            (self.auth/name).write_bytes(c.canonical({'literal':'authenticated-input stub'}))
        self.go={'head':'a'*40,'tree':'b'*40,'inherited_limits':{n:list(resource.getrlimit(getattr(resource,n))) for n in dir(resource) if n.startswith('RLIMIT_')},'diagnostic_files_sha256':{}}
        self.go['inherited_limits']['RLIMIT_AS']=[-1,-1]
        self.go['loader_pin'] = copy.deepcopy(LITERAL_LOADER_PIN)
        self.prov={'workflow_run':'123','workflow_attempt':'1','attempt_path':str(self.attempt),'durable_root':str(self.root)}
    def patches(self):
        stack=ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(patch.object(d,'ROOT',self.root));stack.enter_context(patch.object(d,'EXPERIMENT',self.experiment))
        stack.enter_context(patch.object(d,'TEST_RECEIPT',self.test_receipt));stack.enter_context(patch.object(d,'SCHEDULE',(FAKE_CELL,)))
        stack.enter_context(patch.dict(os.environ,{'WORKER36_CLAIM_DIRECTORY':str(self.claim),'RUNNER_NAME':'bandido-alcatraz-ci','GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1'}))
        stack.enter_context(patch.object(d,'read_admission',return_value=(self.go,self.prov)))
        stack.enter_context(patch.object(d,'durable_location'))
        stack.enter_context(patch.object(d,'runtime_check',side_effect=lambda:{'literal':'runtime stub','loader':literal_loader_identity()}))
        stack.enter_context(patch.object(d,'install_memory_cap'))
        original_getrlimit=resource.getrlimit
        stack.enter_context(patch.object(resource,'getrlimit',side_effect=lambda kind:(-1,-1) if kind==resource.RLIMIT_AS else original_getrlimit(kind)))
        stack.enter_context(patch.object(d,'read_manifest',return_value={'files':[]}))
        stack.enter_context(patch.object(d,'restore',side_effect=lambda repo,target,manifest,budget:budget.mkdir(target)))
        stack.enter_context(patch.object(d,'verify_files'))
        stack.enter_context(patch.object(d,'publish_preservation_handoff'))
        return stack
    def next_ns(self):
        self.ns += 1
        return self.ns
    def new_attempt(self, label):
        self.attempt = self.root / ('attempt-' + label)
        self.claim = self.root / ('claims-' + label); self.claim.mkdir()
        self.prov['attempt_path'] = str(self.attempt)
        self.timers.handler = self.timers.old; self.timers.timer = (0.0, 0.0)
        self.timers.restoring = False; self.timers.events.clear()
    def sidecars(self):
        return [c.strict_json(path.read_bytes()) for path in sorted(self.attempt.glob('failure-receipt-parent-*.json'))]
    def run_preserve(self, deadline='1600000'):
        with patch.object(d, 'install_memory_cap'), patch.object(d, 'read_admission', return_value=(self.go, self.prov)), \
                patch.object(d, 'loader_identity', side_effect=literal_loader_identity):
            return d.preserve(self.attempt, self.root/'transport', self.root/'verification.json', self.root/'recovery.json',
                admission=self.admission, admission_sha256=c.sha(self.admission.read_bytes()),
                admission_provenance=self.provenance, admission_provenance_sha256=c.sha(self.provenance.read_bytes()),
                expected_head='a'*40, expected_tree='b'*40, expected_workflow_run='123',
                preservation_deadline_monotonic_ms=deadline)
    def run_measure(self):
        return d.measure(self.attempt,self.admission,c.sha(self.admission.read_bytes()),self.provenance,c.sha(self.provenance.read_bytes()))
    def supervisor_result(self,value):
        global STUB_SUPERVISOR_INVOCATIONS
        STUB_SUPERVISOR_INVOCATIONS+=1
        return value
    def read_receipt(self):return c.strict_json((self.attempt/'receipt.json').read_bytes())
    def make_receipt(self,status='execution_complete'):
        self.attempt.mkdir();c.Budget(self.attempt).write(self.attempt/'receipt.json',{'schema':'worker36-attempt-v1','status':status,'failure':None,'actual_starts':0,'phase':'verification_pending' if status=='execution_complete' else 'measurement','completed_prefix':[],
            'resource_totals':{'phase':self.literal_phase()}})
        if status=='execution_complete':self.write_closing_proof()
    def literal_phase(self,cpu=1,wall=1):
        return {'wall_seconds':wall,'cpu_seconds':cpu,'wall_limit_seconds':1800,'cpu_limit_seconds':1800,
                'parent_cpu_seconds':cpu,'reaped_child_cpu_seconds':0,'live_child_cpu_seconds':0}
    def write_closing_proof(self,**updates):
        start=time.monotonic();value={'schema':'worker36-measurement-phase-close-v1','phase':self.literal_phase(2,2),
            'computational_receipt':{'path':'receipt.json',**c.file_info(self.attempt/'receipt.json')},
            'includes_computational_receipt_publication':True,'closing_proof_included_in_measurement':False,
            'measurement_work_after_close':False,'preservation_started_monotonic':start,'preservation_deadline_monotonic':start+600}
        value.update(updates);(self.attempt/'measurement-phase-close.json').write_bytes(c.canonical(value))
    def fake_child(self,*args,**kwargs):
        global STUB_SUPERVISOR_INVOCATIONS
        STUB_SUPERVISOR_INVOCATIONS+=1
        folder=self.attempt/'cells/01';budget=c.Budget(self.attempt);calls={}
        for scope in ('candidate','reference'):
            payload={'literal':'fixed-return-stub','scope':scope};info=budget.write(folder/(scope+'-return.json'),payload)
            budget.write(folder/(scope+'-start.json'),{'literal':'marker-stub'})
            budget.write(folder/(scope+'-capture-confirmed.json'),info)
            calls[scope]={'method_entered':True,'invocation_attempted':True,'start_marker_durable':True,'returned':True,'durable_capture_confirmed':True}
        budget.write(folder/'cell-receipt.json',{'status':'complete','failure':None,'calls':calls,'actual_starts':2,'actual_starts_upper_bound':2,'actual_returns':2,'confirmed_captures':2,'pre_call_markers':2})
        for name in ('source-runtime-preflight.json','cell-start.json','cell-boundaries.json','unmeasured-accounting.json'):
            budget.write(folder/name,{'literal':'committed required stub'})
        budget.write(folder/'active-call.json',{'active':False})
        Path(args[3]).write_bytes(b'')
        return {'status':'completed','reason':'child_exit_zero','exit_code':0,'literal':'supervisor-stub'}
    def test_D01_initial_prerequisites_block(self):
        for phase in ('runtime','source'):
            with self.subTest(phase=phase):
                if self.attempt.exists(): self.attempt=self.root/'second-attempt'
                with self.patches():
                    target='runtime_check' if phase=='runtime' else 'restore'
                    with patch.object(d,target,side_effect=c.IntegrityError('wrong initial '+phase)):
                        self.assertEqual(self.run_measure(),1)
                r=self.read_receipt();self.assertEqual(r['status'],'execution_blocked');self.assertEqual(r['actual_starts'],0)
                # Separate fixed temporary claim slot for the second fault.
                self.claim=self.root/'second-claims';self.claim.mkdir(exist_ok=True)
    def test_D02_one_fabricated_cell_completes_driver(self):
        with self.patches(),patch.object(supervision,'run_child',side_effect=self.fake_child):
            self.assertEqual(self.run_measure(),0)
        r=self.read_receipt();self.assertEqual(r['status'],'execution_complete');self.assertEqual(r['actual_starts'],2)
        self.assertEqual(r['actual_starts_upper_bound'],2);self.assertEqual(r['confirmed_captures'],2)
    def test_D03_later_source_drift_integrity(self):
        with self.patches(),patch.object(d,'verify_files',side_effect=c.IntegrityError('changed frozen bytes')):
            self.assertEqual(self.run_measure(),1)
        self.assertEqual(self.read_receipt()['status'],'integrity_invalid')
    def test_D04_torn_records_terminalize(self):
        self.make_receipt('measuring');folder=self.attempt/'cells/01';folder.mkdir(parents=True)
        (folder/'cell-receipt.json').write_bytes(b'{torn')
        (folder/'candidate-capture-confirmed.json').write_bytes(b'{torn')
        counts=d.reconcile_prefix(self.attempt);self.assertEqual(len(counts['corrupt_evidence']),2)
        result=d.terminalize(self.attempt,c.error_record(OSError('later IO'),'measurement'),counts=counts)
        self.assertEqual(result['status'],'integrity_invalid');self.assertEqual((folder/'cell-receipt.json').read_bytes(),b'{torn')
    def test_D05_os_subclass_stays_infrastructure(self):
        with self.patches():
            def denied(*args,**kwargs):
                global STUB_SUPERVISOR_INVOCATIONS
                STUB_SUPERVISOR_INVOCATIONS+=1
                folder=self.attempt/'cells/01';failure=c.error_record(PermissionError('denied'),'cell_measurement')
                c.Budget(self.attempt).write(folder/'cell-receipt.json',{'calls':{},'failure':failure,'status':failure['status']})
                return {'status':'execution_incomplete','reason':'child_nonzero_exit','exit_code':74}
            with patch.object(supervision,'run_child',side_effect=denied):self.assertEqual(self.run_measure(),1)
        self.assertEqual(self.read_receipt()['status'],'execution_incomplete')
    def test_D06_marker_entry_bounds(self):
        self.make_receipt('measuring');folder=self.attempt/'cells/01';folder.mkdir(parents=True)
        (folder/'candidate-start.json').write_bytes(c.canonical({'literal':'pre-call marker'}))
        counts=d.reconcile_prefix(self.attempt);self.assertEqual((counts['actual_starts'],counts['actual_starts_upper_bound']),(0,1))
        (folder/'cell-receipt.json').write_bytes(c.canonical({'calls':{'candidate':{'invocation_attempted':False,'method_entered':False,'returned':False}}}))
        (folder/'candidate-start.json').write_bytes(b'{partial')
        counts=d.reconcile_prefix(self.attempt);self.assertEqual((counts['actual_starts'],counts['actual_starts_upper_bound']),(0,0))
    def test_D07_integrity_survives_later_receipt_failure(self):
        self.make_receipt('measuring');original=c.Budget.write
        def fail_receipt(self,path,value,**kwargs):
            if Path(path).name=='receipt.json':raise OSError('later write failed')
            return original(self,path,value,**kwargs)
        with patch.object(c.Budget,'write',fail_receipt):
            result=d.terminalize(self.attempt,c.error_record(c.IntegrityError('original mismatch'),'measurement'))
        self.assertEqual(result['status'],'integrity_invalid')
        self.assertTrue(list(self.attempt.glob('failure-receipt-parent-*.json')))
    def test_D08_corrupt_main_preserved(self):
        self.make_receipt();p=self.attempt/'receipt.json';p.write_bytes(b'bad original')
        result=d.terminalize(self.attempt,c.error_record(OSError('IO'),'measurement'))
        self.assertEqual(result['status'],'integrity_invalid');self.assertEqual(p.read_bytes(),b'bad original')
        self.assertTrue(list(self.attempt.glob('failure-receipt-parent-*.json')))
    def preservation(self,package_effect):
        with patch.object(verification,'verify_attempt',side_effect=c.IntegrityError('fixed offline mismatch')),patch.object(transport,'package_attempt',side_effect=package_effect):
            return self.run_preserve()
    def test_D09_offline_failure_preserves_and_stays_failed(self):
        self.make_receipt();observed=[]
        def package(*args,**kwargs):observed.append(True);return {'status':'packaged'}
        self.assertEqual(self.preservation(package),1);self.assertEqual(observed,[True])
        self.assertEqual(self.read_receipt()['status'],'integrity_invalid')
        self.assertFalse(c.strict_json((self.root/'verification.json').read_bytes())['complete'])
    def test_D10_partial_packaging_retained(self):
        self.make_receipt()
        def package(root,destination,**kwargs):
            destination.mkdir();(destination/'attempt.zip.partial').write_bytes(b'fixed partial bytes');return {'status':'blocked','error':'fixed write fault'}
        self.assertEqual(self.preservation(package),1)
        self.assertEqual((self.root/'transport/attempt.zip.partial').read_bytes(),b'fixed partial bytes')
        recovery=c.strict_json((self.root/'recovery.json').read_bytes());self.assertTrue(recovery['no_cleanup']);self.assertIn('retained_inventory',recovery)
    def test_D11_actual_test_receipt_and_checked_bytes(self):
        repo=self.root/'repo';repo.mkdir();path=repo/'experiments/synthetic-profile-overhead/focused-recovery-r1-test-receipt.json';path.parent.mkdir(parents=True)
        source=repo/'literal.py';source.write_bytes(b'# fixed source stub\n')
        record={'success':True,'failures':0,'errors':0,'candidate_evaluator_calls':0,'reference_evaluator_calls':0,'games':0,'measurement_fixture_constructions':0,'historical_source_imports':0,'checked_file_sha256':{'literal.py':c.sha(source.read_bytes())}}
        path.write_bytes(c.canonical(record));pin=c.sha(path.read_bytes())
        with patch.object(d,'checked_source_paths',return_value={'literal.py'}):
            d.verify_test_receipt(repo,pin)
            with self.assertRaises(c.IntegrityError):d.verify_test_receipt(repo,'0'*64)
            source.write_bytes(b'# changed\n')
            with self.assertRaises(c.IntegrityError):d.verify_test_receipt(repo,pin)
        checked = d.checked_source_paths(ROOT)
        self.assertIn('scripts/worker36-loader.sh', checked)
        self.assertIn('scripts/worker36/common.py', checked)
        self.assertTrue({path.relative_to(ROOT).as_posix() for path in (ROOT/'evidence-design').glob('recovery-r1-*-test-plan.json')} <= checked)
    def test_D12_offline_memory_cap_exact(self):
        frozen=(512*1024**2,)*2
        with patch.object(resource,'getrlimit',side_effect=[(-1,-1),frozen]),patch.object(resource,'setrlimit') as setting:
            d.install_memory_cap();setting.assert_called_once_with(resource.RLIMIT_AS,frozen)
        with patch.object(resource,'getrlimit',return_value=(1024,1024)),patch.object(resource,'setrlimit') as setting:
            with self.assertRaises(c.IntegrityError):d.install_memory_cap()
            setting.assert_not_called()

    def test_D13_child_integrity_before_supervisor_cap(self):
        original=c.Budget.write
        def fault(budget,path,value,**kwargs):
            if Path(path).name=='supervisor-cell-01.json':raise c.ResourceExceeded('later output ceiling')
            return original(budget,path,value,**kwargs)
        def child(*args,**kwargs):
            global STUB_SUPERVISOR_INVOCATIONS
            STUB_SUPERVISOR_INVOCATIONS+=1
            failure=c.error_record(c.IntegrityError('durable original mismatch'),'cell_measurement')
            c.Budget(self.attempt).write(self.attempt/'cells/01/cell-receipt.json',{'calls':{},'status':'integrity_invalid','failure':failure})
            return {'status':'execution_incomplete','exit_code':65,'reason':'child_nonzero_exit'}
        with self.patches(),patch.object(supervision,'run_child',side_effect=child),patch.object(c.Budget,'write',fault):
            self.assertEqual(self.run_measure(),1)
        r=self.read_receipt();self.assertEqual(r['status'],'integrity_invalid');self.assertEqual(r['failure']['error'],'durable original mismatch')
        self.assertTrue(any(x['status']=='resource_incomplete' for x in r['secondary_errors']))
    def test_D14_exit65_before_supervisor_io(self):
        original=c.Budget.write
        def fault(budget,path,value,**kwargs):
            if Path(path).name=='supervisor-cell-01.json':raise PermissionError('later parent IO')
            return original(budget,path,value,**kwargs)
        with self.patches(),patch.object(supervision,'run_child',side_effect=lambda *a,**k:self.supervisor_result({'status':'execution_incomplete','exit_code':65,'reason':'typed child exit'})),patch.object(c.Budget,'write',fault):
            self.assertEqual(self.run_measure(),1)
        r=self.read_receipt();self.assertEqual(r['status'],'integrity_invalid')
        self.assertTrue(any(x['status']=='execution_incomplete' for x in r['secondary_errors']))
    def test_D15_preserve_measuring_terminalizes(self):
        self.make_receipt('measuring')
        path=self.attempt/'receipt.json';value=self.read_receipt();value.update(phase='measurement',completed_prefix=[])
        path.write_bytes(c.canonical(value))
        self.assertEqual(self.preservation(lambda *a,**k:{'status':'packaged'}),1)
        r=self.read_receipt();self.assertEqual(r['status'],'execution_incomplete');self.assertEqual(r['prior_status'],'measuring')
        self.assertEqual(r['prior_phase'],'measurement')
        gate=c.strict_json((self.root/'verification.json').read_bytes())
        self.assertEqual(gate['failure']['status'],'execution_incomplete');self.assertEqual(gate['failure']['prior_status'],'measuring')
    def test_D16_preserve_child_sidecar_integrity(self):
        self.make_receipt('measuring');failure=c.error_record(c.IntegrityError('surviving child mismatch'),'cell_measurement')
        c.Budget(self.attempt).write(self.attempt/'failure-receipt-cell-01.json',{'status':'integrity_invalid','failure':failure,'calls':{}})
        self.assertEqual(self.preservation(lambda *a,**k:{'status':'packaged'}),1)
        self.assertEqual(self.read_receipt()['failure']['error'],'surviving child mismatch')
        gate=c.strict_json((self.root/'verification.json').read_bytes());self.assertEqual(gate['failure']['status'],'integrity_invalid')
    def test_D17_read_io_is_gap(self):
        self.make_receipt('measuring');folder=self.attempt/'cells/01';folder.mkdir(parents=True)
        target=folder/'candidate-start.json';target.write_bytes(c.canonical({'literal':'marker'}));original=Path.open
        for error in (PermissionError('denied'),FileNotFoundError('disappeared after stat')):
            with self.subTest(error=type(error).__name__):
                def failing(path,*a,**k):
                    if path==target:raise error
                    return original(path,*a,**k)
                with patch.object(Path,'open',failing):counts=d.reconcile_prefix(self.attempt)
                self.assertEqual(counts['corrupt_evidence'],[]);self.assertTrue(counts['unavailable_evidence'])
                self.assertEqual((counts['actual_starts'],counts['actual_starts_upper_bound']),(0,1))
                result,_=d.reduce_failure(c.error_record(error,'measurement'),counts)
                self.assertEqual(result['status'],'execution_incomplete')
    def test_D18_stat_io_is_gap(self):
        self.make_receipt('measuring');folder=self.attempt/'cells/01';folder.mkdir(parents=True)
        target=folder/'candidate-start.json';original=Path.lstat
        def failing(path,*a,**k):
            if path==target:raise PermissionError('stat denied')
            return original(path,*a,**k)
        with patch.object(Path,'lstat',failing):counts=d.reconcile_prefix(self.attempt)
        self.assertFalse(counts['corrupt_evidence']);self.assertTrue(counts['unavailable_evidence'])
        returned=folder/'candidate-return.json';info=c.Budget(self.attempt).write(returned,{'literal':'return'})
        c.Budget(self.attempt).write(folder/'candidate-capture-confirmed.json',info)
        with patch.object(d,'file_info',side_effect=OSError('return stat unavailable')):counts=d.reconcile_prefix(self.attempt)
        self.assertFalse(counts['corrupt_evidence']);self.assertTrue(counts['unavailable_evidence'])
    def test_D19_later_child_preflight_is_incomplete(self):
        self.make_receipt('measuring');folder=self.attempt/'cells/01';folder.mkdir(parents=True)
        c.Budget(self.attempt).write(folder/'cell-receipt.json',{'calls':{'candidate':{'returned':True,'method_entered':True}}})
        failure=c.error_record(PermissionError('later prerequisite unavailable'),'cell_source_runtime_preflight')
        c.Budget(self.attempt).write(self.attempt/'cells/02/cell-receipt.json',{'status':'execution_blocked','failure':failure,'calls':{}})
        r=d.terminalize(self.attempt,failure);self.assertEqual(r['status'],'execution_incomplete')
        self.assertEqual(r['failure']['prior_status'],'execution_blocked')
    def test_D20_later_prespawn_is_incomplete(self):
        calls=[]
        def children(*a,**k):
            calls.append(True)
            if len(calls)==1:return self.fake_child(*a,**k)
            return self.supervisor_result({'status':'execution_blocked','reason':'later unavailable supervision','exit_code':None})
        second={**FAKE_CELL,'cell':2}
        with self.patches(),patch.object(d,'SCHEDULE',(FAKE_CELL,second)),patch.object(supervision,'run_child',side_effect=children):
            self.assertEqual(self.run_measure(),1)
        r=self.read_receipt();self.assertEqual(r['status'],'execution_incomplete');self.assertEqual(r['completed_prefix'],[1])
    def test_D21_first_prespawn_zero_blocked(self):
        with self.patches(),patch.object(supervision,'run_child',side_effect=lambda *a,**k:self.supervisor_result({'status':'execution_blocked','reason':'supervision unavailable','exit_code':None})):
            self.assertEqual(self.run_measure(),1)
        r=self.read_receipt();self.assertEqual(r['status'],'execution_blocked');self.assertEqual(r['actual_starts_upper_bound'],0)
    def test_D22_surviving_parent_and_supervisor_integrity(self):
        self.make_receipt('measuring');budget=c.Budget(self.attempt)
        budget.write(self.attempt/'supervisor-cell-01.json',{'status':'execution_incomplete','exit_code':65,'reason':'typed exit'})
        failure=c.error_record(c.IntegrityError('earlier parent mismatch'),'measurement')
        budget.write(self.attempt/'failure-receipt-parent-1.json',{'status':'integrity_invalid','failure':failure})
        r=d.terminalize(self.attempt,c.error_record(c.ResourceExceeded('later ceiling'),'measurement'))
        self.assertEqual(r['status'],'integrity_invalid');self.assertTrue(any(x['status']=='resource_incomplete' for x in r['secondary_errors']))
        self.assertTrue(any(x['evidence_path']=='failure-receipt-parent-1.json' for x in r['retained_failures']))
    def test_D23_main_receipt_io_uses_sidecar(self):
        self.make_receipt('measuring');target=self.attempt/'receipt.json';original=Path.open
        def failing(path,*a,**k):
            if path==target:raise PermissionError('main unreadable')
            return original(path,*a,**k)
        with patch.object(Path,'open',failing):
            with self.assertRaises(PermissionError):c.update_receipt(self.attempt,status='measuring')
            r=d.terminalize(self.attempt,c.error_record(PermissionError('IO'),'measurement'))
        self.assertEqual(r['status'],'execution_incomplete');self.assertFalse(r['corrupt_evidence'])
        self.assertTrue(list(self.attempt.glob('failure-receipt-parent-*.json')))
    def test_D24_reducer_resource_and_uncertainty(self):
        counts={'actual_starts':0,'actual_starts_upper_bound':1,'capture_gaps':[{'literal':'unknown entry'}],'unavailable_evidence':[],'corrupt_evidence':[],'retained_failures':[]}
        for status,expected in (('resource_incomplete','resource_incomplete'),('measuring','execution_incomplete'),('execution_blocked','execution_incomplete')):
            with self.subTest(status=status):
                result,_=d.reduce_failure({'status':status,'phase':'measurement','error':'literal'},counts)
                self.assertEqual(result['status'],expected)

    def transient_read_case(self,error,expected):
        original=Path.open;failed=[];target=self.attempt/'cells/01/candidate-return.json'
        def unavailable(path,*a,**k):
            if path==target and not failed:
                failed.append(True);raise error
            return original(path,*a,**k)
        original_reconcile=d.reconcile_prefix
        def reconcile(root):
            with patch.object(Path,'open',unavailable):return original_reconcile(root)
        with self.patches(),patch.object(supervision,'run_child',side_effect=self.fake_child) as spawn,patch.object(d,'reconcile_prefix',side_effect=reconcile):
            self.assertEqual(self.run_measure(),1);self.assertEqual(spawn.call_count,1)
        r=self.read_receipt();self.assertEqual(r['status'],expected);self.assertTrue(r['unavailable_evidence'])
        self.assertEqual(r['failure']['error_type'],type(error).__name__)
        with patch.object(d,'SCHEDULE',(FAKE_CELL,)):
            fresh=original_reconcile(self.attempt)
        self.assertFalse(fresh['unavailable_evidence'])
        terminal=d.terminalize(self.attempt,c.error_record(OSError('later recovery'),'preservation'),counts=fresh)
        self.assertEqual(terminal['status'],expected)
        return terminal
    def test_D25_transient_required_read_stops(self):
        self.transient_read_case(PermissionError('one required read denied'),'execution_incomplete')
    def test_D26_transient_memory_stops(self):
        self.transient_read_case(MemoryError('one required read exhausted'),'resource_incomplete')
    def test_D27_malformed_retained_matrix(self):
        self.make_receipt('measuring');path=self.attempt/'supervisor-cell-01.json'
        valid=c.error_record(c.IntegrityError('literal mismatch'),'measurement')
        cases=[{'status':x} for x in ([],{},True,1,'unknown')]+[
            {'status':'execution_incomplete','failure':[]},
            {'status':'execution_incomplete','failure':{'status':[]}},
            {'status':'resource_incomplete','failure':valid}]
        for value in cases:
            with self.subTest(value=value):
                path.write_bytes(c.canonical(value));counts=d.reconcile_prefix(self.attempt)
                outcome=d.terminalize(self.attempt,c.error_record(OSError('recovery'),'preservation'),counts=counts)
                self.assertEqual(outcome['status'],'integrity_invalid');self.assertEqual(self.read_receipt()['status'],'integrity_invalid')
    def test_D28_supervisor_resource_and_exit_are_distinct(self):
        counts={'actual_starts_upper_bound':0,'capture_gaps':[],'unavailable_evidence':[],'corrupt_evidence':[],'retained_failures':[]}
        for code in (65,74,75,78):
            with self.subTest(code=code):
                value={'status':'resource_incomplete','reason':'call_wall_limit','exit_code':code,
                       'primary_outcome':{'status':'resource_incomplete','reason':'call_wall_limit'},
                       'secondary_failures':[{'status':'execution_incomplete','reason':'process_cleanup_unconfirmed','phase':'cleanup'}]}
                causes=d._retained_failures(value,'literal-supervisor');r,secondary=d.reduce_failure(None,counts,additional=causes)
                self.assertEqual(r['status'],'integrity_invalid' if code==65 else 'resource_incomplete')
                self.assertTrue(any(x['category']=='typed_child_exit' for x in [r,*secondary]))
                self.assertTrue(any(x['category']=='supervisor_secondary' for x in [r,*secondary]))
        original=d.reconcile_prefix;observed=[]
        def interruption(root):
            if not observed:
                observed.append(True);raise c.ResourceExceeded('deadline interrupted first reconciliation')
            return original(root)
        with self.patches(),patch.object(supervision,'run_child',side_effect=lambda *a,**k:self.supervisor_result({'status':'execution_incomplete','reason':'typed exit before scan','exit_code':65})),patch.object(d,'reconcile_prefix',side_effect=interruption):
            self.assertEqual(self.run_measure(),1)
        self.assertEqual(self.read_receipt()['status'],'integrity_invalid')
    def test_D29_torn_staging_is_uncertainty(self):
        self.make_receipt('measuring');path=self.attempt/'cells/01/candidate-start.json.tmp';path.parent.mkdir(parents=True);path.write_bytes(b'{partial')
        counts=d.reconcile_prefix(self.attempt);self.assertEqual(counts['corrupt_evidence'],[])
        self.assertEqual((counts['actual_starts'],counts['actual_starts_upper_bound']),(0,1))
        for error,status in ((c.ResourceExceeded('output ceiling'),'resource_incomplete'),(OSError('interrupted publication'),'execution_incomplete')):
            with self.subTest(status=status):
                result,_=d.reduce_failure(c.error_record(error,'measurement'),counts);self.assertEqual(result['status'],status)
        self.assertEqual(path.read_bytes(),b'{partial');self.assertEqual(counts['unavailable_evidence'][0]['evidence_state'],'uncommitted')
    def test_D30_unavailable_types_preserved(self):
        self.make_receipt('measuring');folder=self.attempt/'cells/01';folder.mkdir(parents=True)
        path=folder/'candidate-return.json';path.write_bytes(c.canonical({'literal':'return'}));original=Path.open
        for error,status in ((PermissionError('denied'),'execution_incomplete'),(MemoryError('memory'),'resource_incomplete'),(RecursionError('parser capacity'),'resource_incomplete')):
            with self.subTest(error=type(error).__name__):
                def unavailable(target,*a,**k):
                    if target==path:raise error
                    return original(target,*a,**k)
                with patch.object(Path,'open',unavailable):counts=d.reconcile_prefix(self.attempt)
                result,_=d.reduce_failure(None,counts);self.assertEqual(result['status'],status);self.assertFalse(counts['corrupt_evidence'])
        info={'path':'cells/01/candidate-return.json',**c.file_info(path)};c.Budget(self.attempt).write(folder/'candidate-capture-confirmed.json',info)
        with patch.object(d,'file_info',side_effect=MemoryError('capture metadata memory')):counts=d.reconcile_prefix(self.attempt)
        result,_=d.reduce_failure(None,counts);self.assertEqual(result['status'],'resource_incomplete')
    def test_D31_malformed_failure_fields(self):
        counts={'actual_starts_upper_bound':0,'capture_gaps':[],'unavailable_evidence':[],'corrupt_evidence':[],'retained_failures':[]}
        failure=c.error_record(OSError('literal'),'measurement')
        cases=[{'status':'execution_incomplete','failure':{**failure,key:[]}} for key in ('category','phase','error_type','error')]
        cases += [{'status':'execution_incomplete','secondary_errors':value} for value in ({},[None])]
        for value in cases:
            with self.subTest(value=value):
                result,_=d.reduce_failure(None,counts,additional=d._retained_failures(value,'literal-committed'))
                self.assertEqual(result['status'],'integrity_invalid')
    def test_D32_recorded_unavailable_failure_stays_terminal(self):
        self.make_receipt('measuring');counts=d.reconcile_prefix(self.attempt)
        counts['unavailable_evidence']=[d._unavailable('cells/01/candidate-return.json',MemoryError('observed before readable'))]
        r=d.terminalize(self.attempt,None,counts=counts);self.assertEqual(r['status'],'resource_incomplete')
        fresh=d.reconcile_prefix(self.attempt);self.assertFalse(fresh['unavailable_evidence'])
        r=d.terminalize(self.attempt,{'status':'execution_complete','phase':'late_scan','error':'now readable'},counts=fresh)
        self.assertEqual(r['status'],'resource_incomplete')
    def test_D33_malformed_direct_causes_do_not_escape(self):
        counts={'actual_starts_upper_bound':0,'capture_gaps':[],'unavailable_evidence':[],'corrupt_evidence':[],'retained_failures':[]}
        for primary,additional in (({'status':[]},()),(None,({'status':{}},)),([],())):
            with self.subTest(primary=primary,additional=additional):
                result,_=d.reduce_failure(primary,counts,additional=additional);self.assertEqual(result['status'],'integrity_invalid')
    def test_D34_final_reconciliation_failure_stops(self):
        original=d.reconcile_prefix;scans=[]
        def reconcile(root):
            counts=original(root);scans.append(True)
            if len(scans)==2:counts['unavailable_evidence'].append(d._unavailable('cells/01/candidate-return.json',PermissionError('final scan denied')))
            return counts
        with self.patches(),patch.object(supervision,'run_child',side_effect=self.fake_child) as spawn,patch.object(d,'reconcile_prefix',side_effect=reconcile):
            self.assertEqual(self.run_measure(),1);self.assertEqual(spawn.call_count,1)
        r=self.read_receipt();self.assertEqual(r['status'],'execution_incomplete');self.assertTrue(r['unavailable_evidence'])

    def absent_completed_event(self,name,*,two_cells=False,mutate=None):
        def child(*a,**k):
            result=self.fake_child(*a,**k)
            if name:(self.attempt/'cells/01'/name).unlink()
            if mutate:
                path=self.attempt/'cells/01/cell-receipt.json';value=c.strict_json(path.read_bytes());mutate(value);path.write_bytes(c.canonical(value))
            return result
        with self.patches(),patch.object(d,'SCHEDULE',(FAKE_CELL,{**FAKE_CELL,'cell':2}) if two_cells else (FAKE_CELL,)),patch.object(supervision,'run_child',side_effect=child) as spawn:
            self.assertEqual(self.run_measure(),1);self.assertEqual(spawn.call_count,1)
        self.assertFalse((self.attempt/'measurement-phase-close.json').exists())
        return self.read_receipt()
    def test_D35_missing_candidate_confirmation_stops(self):
        r=self.absent_completed_event('candidate-capture-confirmed.json',two_cells=True)
        self.assertEqual(r['status'],'integrity_invalid');self.assertEqual(r['confirmed_captures'],1);self.assertTrue(r['capture_gaps'])
    def test_D36_missing_candidate_start_stops(self):
        r=self.absent_completed_event('candidate-start.json',two_cells=True)
        self.assertEqual(r['status'],'integrity_invalid');self.assertEqual(r['pre_call_markers'],1);self.assertTrue(r['capture_gaps'])
    def test_D37_missing_candidate_return_stops(self):
        r=self.absent_completed_event('candidate-return.json');self.assertEqual(r['status'],'integrity_invalid')
        self.assertEqual(r['actual_starts'],2);self.assertTrue(r['capture_gaps'])
    def test_D38_completed_claim_matrix(self):
        cases=[('reference-start.json',None),('reference-capture-confirmed.json',None),
               (None,lambda v:v['calls'].pop('candidate')),
               (None,lambda v:v['calls']['candidate'].update(start_marker_durable=False))]
        for index,(name,mutate) in enumerate(cases):
            with self.subTest(index=index):
                self.attempt=self.root/('event-attempt-'+str(index));self.claim=self.root/('event-claims-'+str(index));self.claim.mkdir()
                r=self.absent_completed_event(name,mutate=mutate);self.assertEqual(r['status'],'integrity_invalid')
    def test_D39_final_phase_cpu_boundary(self):
        original=supervision.PhaseBudget.snapshot;seen=[]
        def snapshot(phase,*a,**k):
            value=original(phase,*a,**k);seen.append(True)
            if len(seen)==3:value.update(cpu_seconds=1800,parent_cpu_seconds=1800)
            return value
        with self.patches(),patch.object(supervision,'run_child',side_effect=self.fake_child),patch.object(supervision.PhaseBudget,'snapshot',snapshot):
            self.assertEqual(self.run_measure(),1)
        self.assertEqual(self.read_receipt()['status'],'resource_incomplete');self.assertFalse((self.attempt/'measurement-phase-close.json').exists())
    def test_D40_publication_cpu_included(self):
        original_write=c.Budget.write;original_snapshot=supervision.PhaseBudget.snapshot;published=[]
        def write(budget,path,value,**kwargs):
            result=original_write(budget,path,value,**kwargs)
            if Path(path).name=='receipt.json' and isinstance(value,dict) and value.get('status')=='execution_complete':published.append(True)
            return result
        def snapshot(phase,*a,**k):
            value=original_snapshot(phase,*a,**k)
            if published:value.update(cpu_seconds=1800,parent_cpu_seconds=1800)
            return value
        with self.patches(),patch.object(supervision,'run_child',side_effect=self.fake_child),patch.object(c.Budget,'write',write),patch.object(supervision.PhaseBudget,'snapshot',snapshot):
            self.assertEqual(self.run_measure(),1)
        self.assertTrue(published);self.assertEqual(self.read_receipt()['status'],'resource_incomplete')
        self.assertFalse((self.attempt/'measurement-phase-close.json').exists())
    def test_D41_offline_resource_types(self):
        for cpu,wall in ((1800,1),(1,1800)):
            with self.subTest(cpu=cpu,wall=wall),self.assertRaises(c.ResourceExceeded):verification._phase(self.literal_phase(cpu,wall))
        with self.assertRaises(c.ResourceExceeded):verification._number(720,720)
        for value in ('1800',float('nan'),-1):
            with self.subTest(value=value),self.assertRaises(c.IntegrityError):verification._number(value,1800)
    def test_D42_gap_without_primary_stops(self):
        counts={'actual_starts_upper_bound':1,'capture_gaps':[{'literal':'required capture gap'}],'corrupt_evidence':[],'unavailable_evidence':[],'retained_failures':[]}
        result,_=d.reduce_failure(None,counts);self.assertEqual(result['status'],'execution_incomplete')
        counts['corrupt_evidence']=[{'literal':'committed event contradiction'}]
        result,_=d.reduce_failure(None,counts);self.assertEqual(result['status'],'integrity_invalid')
    def test_D43_terminal_memory_classification(self):
        self.make_receipt('measuring');original=c.Budget.write
        def no_main(budget,path,value,**kwargs):
            if Path(path).name=='receipt.json':raise MemoryError('terminal receipt memory')
            return original(budget,path,value,**kwargs)
        with patch.object(c.Budget,'write',no_main):result=d.terminalize(self.attempt,c.error_record(OSError('earlier IO'),'measurement'))
        self.assertEqual(result['status'],'resource_incomplete')
        with patch.object(c.Budget,'write',no_main),patch.object(d,'write_failure_receipt',side_effect=MemoryError('sidecar memory')):
            result=d.terminalize(self.attempt,c.error_record(c.IntegrityError('earlier mismatch'),'measurement'))
        self.assertEqual(result['status'],'integrity_invalid');self.assertEqual(result['terminal_durability'],'unconfirmed')
    def test_D44_timer_restoration_memory_terminal(self):
        self.timers.case = 'handler_after_memory'
        with self.patches(),patch.object(supervision,'run_child',side_effect=self.fake_child):
            self.assertEqual(self.run_measure(),1)
        self.assertEqual(self.read_receipt()['status'],'execution_complete')
        sidecar = self.sidecars()[-1]
        self.assertEqual(sidecar['status'],'resource_incomplete')
        self.assertTrue(any(item.get('restoration_confirmed') is True for item in sidecar['secondary_errors']))
    def test_D45_shared_preservation_deadline(self):
        self.make_receipt(); start=299.0
        self.write_closing_proof(preservation_started_monotonic=start,preservation_deadline_monotonic=899.0)
        original=(self.attempt/'receipt.json').read_bytes()
        with patch.object(verification,'verify_attempt') as verify,patch.object(transport,'package_attempt') as package:
            self.assertEqual(self.run_preserve(),1)
        verify.assert_not_called();package.assert_not_called()
        self.assertEqual((self.attempt/'receipt.json').read_bytes(),original)
        self.assertEqual(self.sidecars()[-1]['status'],'resource_incomplete')
        self.assertEqual(self.sidecars()[-1]['preservation_deadline_monotonic'],899.0)
    def test_D46_closing_proof_required(self):
        self.make_receipt();proof=verification.closing_phase(self.attempt,self.read_receipt())
        self.assertEqual(proof['computational_receipt']['sha256'],c.file_info(self.attempt/'receipt.json')['sha256'])
        (self.attempt/'measurement-phase-close.json').unlink()
        with patch.object(transport,'package_attempt') as package:
            self.assertEqual(self.preservation(package),1)
        package.assert_not_called()
        self.assertEqual(self.sidecars()[-1]['status'],'execution_incomplete')

    def preserve_recording_deadline(self):
        captured=[]
        with patch.object(verification,'verify_attempt') as verify,patch.object(transport,'package_attempt',side_effect=lambda *a,**k:(captured.append(k['deadline_monotonic']) or {'status':'blocked'})):
            code=self.run_preserve()
        verify.assert_not_called();self.assertEqual(code,1)
        return captured
    def test_D47_terminal_status_preserves_closing_deadline(self):
        self.make_receipt();self.write_closing_proof(preservation_started_monotonic=299.0,preservation_deadline_monotonic=899.0)
        anchor=(self.attempt/'measurement-phase-close.json').read_bytes()
        d.terminalize(self.attempt,c.error_record(MemoryError('later restoration resource failure'),'timer_restoration'))
        self.assertNotEqual(c.file_info(self.attempt/'receipt.json')['sha256'],c.strict_json(anchor)['computational_receipt']['sha256'])
        self.assertEqual(self.preserve_recording_deadline(),[]);self.assertEqual(self.read_receipt()['status'],'resource_incomplete')
        self.assertEqual(self.sidecars()[-1]['preservation_deadline_monotonic'],899.0)
        self.assertEqual((self.attempt/'measurement-phase-close.json').read_bytes(),anchor)
    def test_D48_malformed_receipt_keeps_closing_deadline(self):
        self.make_receipt();self.write_closing_proof(preservation_started_monotonic=299.0,preservation_deadline_monotonic=899.0)
        anchor=(self.attempt/'measurement-phase-close.json').read_bytes();(self.attempt/'receipt.json').write_bytes(b'{committed malformed receipt')
        self.assertEqual(self.preserve_recording_deadline(),[])
        self.assertEqual((self.attempt/'receipt.json').read_bytes(),b'{committed malformed receipt')
        self.assertEqual((self.attempt/'measurement-phase-close.json').read_bytes(),anchor)
        sidecar=self.sidecars()[-1]
        self.assertEqual(sidecar['preservation_deadline_monotonic'],899.0)
        self.assertEqual(sidecar['count_evidence'],'unavailable')
        self.assertEqual(sidecar['status'],'resource_incomplete')
    def test_D49_unrecoverable_anchor_never_renews_budget(self):
        original=Path.read_bytes
        for index,fault in enumerate(('denied','malformed')):
            with self.subTest(fault=fault):
                self.root=self.root/('anchor-'+str(index));self.root.mkdir();self.attempt=self.root/'attempt'
                self.make_receipt();path=self.attempt/'measurement-phase-close.json'
                if fault=='malformed':path.write_bytes(b'{bad closing proof')
                raw=original(path)
                def read(target):
                    if target==path and fault=='denied':raise PermissionError('closing anchor unavailable')
                    return original(target)
                with patch.object(Path,'read_bytes',read):deadlines=self.preserve_recording_deadline()
                self.assertEqual(deadlines,[]);self.assertEqual(original(path),raw)
                self.assertEqual(self.sidecars()[-1]['preservation_deadline_monotonic'],1600.0)
                self.assertFalse((self.root/'transport').exists())
    def test_D50_storage_prerequisite_is_not_corruption(self):
        for index,(prior,starts,expected) in enumerate(((None,0,'execution_blocked'),(None,2,'execution_incomplete'),
                ('integrity_invalid',2,'integrity_invalid'),('resource_incomplete',2,'resource_incomplete'))):
            with self.subTest(prior=prior,starts=starts):
                self.root=self.root/('storage-'+str(index));self.root.mkdir();self.attempt=self.root/'attempt';self.make_receipt()
                path=self.attempt/'receipt.json';value=self.read_receipt();value['actual_starts']=starts
                if prior:
                    value['status']=prior;value['failure']={'status':prior,'category':'literal_prior','phase':'measurement',
                        'error_type':'LiteralPriorFailure','error':'fixed earlier cause'}
                path.write_bytes(c.canonical(value));self.write_closing_proof()
                anchor=c.strict_json((self.attempt/'measurement-phase-close.json').read_bytes())
                with patch.object(d.shutil,'disk_usage',return_value=types.SimpleNamespace(free=1024**3-1)):
                    deadlines=self.preserve_recording_deadline()
                self.assertEqual(deadlines,[anchor['preservation_deadline_monotonic']])
                self.assertEqual(self.read_receipt()['status'],expected)
                if prior:self.assertEqual(self.read_receipt()['failure']['error'],'fixed earlier cause')
    def test_D51_staged_anchor_keeps_original_deadline(self):
        for index,age in enumerate((701,10)):
            with self.subTest(age=age):
                self.root=self.root/('staged-'+str(index));self.root.mkdir();self.attempt=self.root/'attempt';self.make_receipt()
                start=time.monotonic()-age;self.write_closing_proof(preservation_started_monotonic=start,preservation_deadline_monotonic=start+600)
                final=self.attempt/'measurement-phase-close.json';staged=final.with_name(final.name+'.tmp');final.rename(staged);raw=staged.read_bytes()
                self.assertEqual(self.preserve_recording_deadline(),[] if age==701 else [1590.0])
                self.assertEqual(staged.read_bytes(),raw);self.assertFalse(final.exists())
                terminal=self.sidecars()[-1] if age==701 else self.read_receipt()
                self.assertEqual(terminal['status'],'resource_incomplete' if age==701 else 'execution_incomplete')
    def test_D52_missing_anchor_after_possible_completion(self):
        for index,kind in enumerate(('complete','terminalized','missing-receipt')):
            with self.subTest(kind=kind):
                self.root=self.root/('missing-'+str(index));self.root.mkdir();self.attempt=self.root/'attempt';self.make_receipt()
                (self.attempt/'measurement-phase-close.json').unlink()
                if kind=='terminalized':d.terminalize(self.attempt,c.error_record(OSError('later restoration failure'),'coordinator_timer_restoration'))
                if kind=='missing-receipt':(self.attempt/'receipt.json').unlink()
                raw=self.attempt/'fixed-prefix.bin';raw.write_bytes(b'literal surviving evidence')
                self.assertEqual(self.preserve_recording_deadline(),[])
                self.assertFalse((self.root/'transport').exists())
                self.assertEqual(raw.read_bytes(),b'literal surviving evidence')
                terminal=self.sidecars()[-1]
                self.assertEqual(terminal['status'],'execution_incomplete')
                self.assertEqual(terminal['count_evidence'],'unavailable')
                self.assertFalse((self.root/'recovery.json').exists())
    def test_D53_torn_or_future_staged_anchor_is_uncertain(self):
        for index,kind in enumerate(('torn','future')):
            with self.subTest(kind=kind):
                self.root=self.root/('uncertain-'+str(index));self.root.mkdir();self.attempt=self.root/'attempt';self.make_receipt()
                if kind=='future':self.write_closing_proof(preservation_started_monotonic=1100.0,preservation_deadline_monotonic=1700.0)
                final=self.attempt/'measurement-phase-close.json';staged=final.with_name(final.name+'.tmp');final.rename(staged)
                if kind=='torn':staged.write_bytes(b'{uncommitted partial anchor')
                raw=staged.read_bytes();self.assertEqual(self.preserve_recording_deadline(),[])
                self.assertEqual(staged.read_bytes(),raw)
                self.assertEqual(self.sidecars()[-1]['status'],'execution_incomplete')
    def test_D54_positive_preclosing_evidence_only(self):
        cases=(('execution_blocked','admission',False),('measuring','measurement',False),('measuring','measurement',True))
        for index,(status,phase,staging) in enumerate(cases):
            with self.subTest(status=status,phase=phase,staging=staging):
                self.root=self.root/('preclosing-'+str(index));self.root.mkdir();self.attempt=self.root/'attempt';self.make_receipt(status)
                path=self.attempt/'receipt.json';value=self.read_receipt();value.update(phase=phase,completed_prefix=[])
                path.write_bytes(c.canonical(value))
                if status=='measuring':d.terminalize(self.attempt,c.error_record(OSError('partial cell unavailable'),'measurement'))
                if staging:(self.attempt/'receipt.json.tmp').write_bytes(b'{possible computational publication')
                self.assertEqual(self.preserve_recording_deadline(),[] if staging else [1600.0])
                if staging:self.assertEqual(self.sidecars()[-1]['count_evidence'],'unavailable')

    def test_R1D01_loader_freeze_precedes_source_restoration(self):
        for differing in (False, True):
            with self.subTest(differing=differing):
                self.new_attempt('loader-' + str(differing))
                loader=literal_loader_identity()
                if differing:loader['library_sha256']='5'*64
                with self.patches(),patch.object(d,'runtime_check',return_value={'loader':loader}), \
                        patch.object(d,'restore',side_effect=lambda repo,target,manifest,budget:budget.mkdir(target)) as restore, \
                        patch.object(supervision,'run_child',side_effect=self.fake_child) as child:
                    self.assertEqual(self.run_measure(),int(differing))
                if differing:
                    restore.assert_not_called();child.assert_not_called()
                    self.assertEqual(self.read_receipt()['status'],'execution_blocked')
                    self.assertEqual(self.read_receipt()['actual_starts'],0)
                else:
                    restore.assert_called_once();child.assert_called_once()
                    self.assertEqual(c.strict_json((self.attempt/'source-runtime-preflight.json').read_bytes())['runtime']['loader'],loader)
                    self.assertEqual(self.read_receipt()['status'],'execution_complete')

    def handoff_patches(self, output):
        stack=ExitStack();self.addCleanup(stack.close)
        stack.enter_context(patch.dict(os.environ,{'GITHUB_OUTPUT':str(output)}))
        original=Path.read_text
        def read(path,*a,**k):
            if str(path)=='/proc/sys/kernel/random/boot_id':return LITERAL_BOOT_ID+'\n'
            return original(path,*a,**k)
        stack.enter_context(patch.object(Path,'read_text',read))
        return stack

    def test_R1D02_paired_handoff_clock_order_and_floor(self):
        output=self.root/'github-output';output.write_bytes(b'')
        events=[]
        def boot(clock):events.append(('boot',clock));return 1200.1259
        def mono():events.append(('mono',));return 1000.0009
        with self.handoff_patches(output),patch.object(time,'clock_gettime',side_effect=boot), \
                patch.object(time,'monotonic',side_effect=mono):
            value=d.publish_preservation_handoff(1500.0004)
        self.assertEqual(events[:2],[('boot',time.CLOCK_BOOTTIME),('mono',)])
        self.assertEqual(value,{'preservation_deadline_monotonic_ms':'1500000',
            'preservation_deadline_boottime_ms':'1700125','preservation_boot_id':LITERAL_BOOT_ID})
        self.assertEqual(output.read_bytes(),('preservation_deadline_monotonic_ms=1500000\n'
            'preservation_deadline_boottime_ms=1700125\npreservation_boot_id='+LITERAL_BOOT_ID+'\n').encode())

    def test_R1D03_handoff_publication_failures_never_retry(self):
        real_write=os.write
        for index,kind in enumerate(('absent','relative','symlink','partial','write_error','fsync_error')):
            with self.subTest(kind=kind):
                output=self.root/('github-output-'+str(index));output.write_bytes(b'')
                target=output
                if kind=='symlink':
                    target=self.root/'github-output-link';target.symlink_to(output)
                writes=[]
                def write(fd,raw):
                    writes.append(raw)
                    if kind=='write_error':raise OSError('literal append unavailable')
                    if kind=='partial':return real_write(fd,raw[:11])
                    return real_write(fd,raw)
                with self.handoff_patches(target),patch.object(os,'write',side_effect=write), \
                        patch.object(os,'fsync',side_effect=OSError('literal fsync unconfirmed') if kind=='fsync_error' else None):
                    if kind=='absent':os.environ.pop('GITHUB_OUTPUT',None)
                    if kind=='relative':os.environ['GITHUB_OUTPUT']='relative-output'
                    with self.assertRaises((c.IntegrityError,OSError)):d.publish_preservation_handoff(1500.0)
                self.assertEqual(len(writes),0 if kind in ('absent','relative','symlink') else 1)
                if kind=='partial':self.assertEqual(output.read_bytes(),writes[0][:11])
                elif kind!='fsync_error':self.assertEqual(output.read_bytes(),b'')

    def test_R1D04_invalid_incoming_handoff_stops_bulk_work(self):
        for index,value in enumerate((None,'','malformed','0','-1','1000000','1600001')):
            with self.subTest(value=value):
                self.new_attempt('incoming-'+str(index));self.make_receipt('measuring')
                before=(self.attempt/'receipt.json').read_bytes()
                with patch.object(d,'_preserve') as bulk,patch.object(d,'reconcile_prefix') as reconcile, \
                        patch.object(c.Budget,'inventory') as inventory,patch.object(transport,'package_attempt') as package:
                    self.assertEqual(self.run_preserve(value),1)
                for call in (bulk,reconcile,inventory,package):call.assert_not_called()
                self.assertFalse(any(event[0]=='timer' and event[2]>0 for event in self.timers.events))
                self.assertEqual((self.attempt/'receipt.json').read_bytes(),before)
                self.assertEqual(len(self.sidecars()),1)
                self.assertEqual(self.sidecars()[0]['count_evidence'],'unavailable')

    def test_R1D05_original_handoff_clamps_final_or_staged_anchor(self):
        for index,(staged,anchor_deadline,terminal) in enumerate(((False,1500.0,False),
                (True,1500.0,True),(False,1700.0,True),(True,1700.0,False))):
            with self.subTest(staged=staged,anchor=anchor_deadline,terminal=terminal):
                self.root=self.root/('clamp-'+str(index));self.root.mkdir();self.attempt=self.root/'attempt'
                self.now=1100.0;self.make_receipt()
                self.write_closing_proof(preservation_started_monotonic=anchor_deadline-600,
                    preservation_deadline_monotonic=anchor_deadline)
                path=self.attempt/'measurement-phase-close.json'
                if staged:path.rename(path.with_name(path.name+'.tmp'));path=path.with_name(path.name+'.tmp')
                original=path.read_bytes()
                if terminal:d.terminalize(self.attempt,c.error_record(c.IntegrityError('prior fixed mismatch'),'measurement'))
                deadlines=[]
                with patch.object(verification,'verify_attempt',side_effect=c.IntegrityError('fixed offline mismatch')), \
                        patch.object(transport,'package_attempt',side_effect=lambda *a,**k:(deadlines.append(k['deadline_monotonic']) or {'status':'packaged'})):
                    self.assertEqual(self.run_preserve('1600000'),1)
                expected=min(1600.0,anchor_deadline)
                self.assertEqual(deadlines,[expected]);self.assertEqual(path.read_bytes(),original)
                self.assertEqual(c.strict_json((self.root/'recovery.json').read_bytes())['deadline_monotonic'],expected)
                self.assertTrue(all(event[2]<=500 for event in self.timers.events if event[0]=='timer' and event[2]>0))
                self.timers.events.clear();self.timers.restoring=False

    def test_R1D06_failure_arms_original_cutoff_before_terminalization(self):
        with self.subTest(boundary='terminalization_exceeds_original_cutoff'):
            events=[]
            def fail(*a,**k):self.now=1900.0;raise c.IntegrityError('fixed first failure')
            def terminal(*a,**k):
                events.append(('terminal',self.now,k['deadline']))
                self.assertIn(('timer',1900.0,600.0),self.timers.events)
                self.now=2601.0;raise d.PreservationExpired()
            with self.patches(),patch.object(d,'verify_files',side_effect=fail), \
                    patch.object(d,'terminalize',side_effect=terminal) as terminal_call, \
                    patch.object(d,'publish_preservation_handoff',side_effect=lambda deadline:events.append(('handoff',self.now,deadline))):
                self.assertEqual(self.run_measure(),1)
            terminal_call.assert_called_once()
            self.assertEqual(events,[('handoff',1900.0,2500.0),('terminal',1900.0,2500.0)])
            self.assertEqual([e[2] for e in self.timers.events if e[0]=='timer' and e[2]>0],[1800,600.0])
            self.assertEqual(self.sidecars()[-1]['preservation_deadline_monotonic'],2500.0)
            self.assertEqual(self.sidecars()[-1]['status'],'integrity_invalid')
        with self.subTest(boundary='fresh_arm_clock_after_delay'):
            self.new_attempt('arm-delay');self.now=100.0
            actual_arm=d.arm_preservation_until
            def delayed_arm(deadline):self.now=699.0;return actual_arm(deadline)
            with self.patches(),patch.object(d,'verify_files',side_effect=c.IntegrityError('fixed first failure at100')), \
                    patch.object(d,'arm_preservation_until',side_effect=delayed_arm), \
                    patch.object(d,'publish_preservation_handoff') as handoff:
                self.assertEqual(self.run_measure(),1)
            handoff.assert_called_once_with(700.0)
            self.assertEqual([e[2] for e in self.timers.events if e[0]=='timer' and e[2]>0],[1800,1.0])

    def test_R1D07_actual_supervisor_callback_arms_before_persistence(self):
        import test_worker36_supervision as supervisor_tests
        actual_run=supervision.run_child
        results=[];harnesses=[];retained=d._retained_failures
        def child(*args,**kwargs):
            global STUB_SUPERVISOR_INVOCATIONS
            STUB_SUPERVISOR_INVOCATIONS+=1
            with patch.object(supervisor_tests,'supervision',supervision), \
                    supervisor_tests.LiteralSupervisorBoundaryHarness(self.attempt,'resource_late_fsync') as h:
                h.error_factory=c.ResourceExceeded;harnesses.append(h)
                def timer(which,seconds,interval=0):
                    self.now=h.now
                    h.events.append(('driver_alarm',h.now,seconds))
                    return self.timers.setitimer(which,seconds,interval)
                def observe(value,path):
                    if path=='first_supervisor_failure':
                        self.assertEqual(value['first_failure_monotonic'],1900.0)
                        self.assertIn(('driver_alarm',1900.0,600.0),h.events)
                        h.events.append(('driver_metadata',h.now))
                    return retained(value,path)
                with patch.object(d.signal,'setitimer',side_effect=timer), \
                        patch.object(d,'_retained_failures',side_effect=observe), \
                        patch.object(supervision,'_inherited_limits',return_value=kwargs['expected_inherited_limits']):
                    result=actual_run(*args,**kwargs)
                self.now=h.now;results.append(result);return result
        with self.patches(),patch.object(supervision,'run_child',side_effect=child) as run, \
                patch.object(d,'publish_preservation_handoff') as handoff:
            self.assertEqual(self.run_measure(),1)
        run.assert_called_once();handoff.assert_not_called()
        result=results[0];h=harnesses[0]
        self.assertEqual(result['preservation_deadline_monotonic'],2500.0)
        self.assertTrue(result['preservation_expired'])
        arm=next(i for i,e in enumerate(h.events) if e[0]=='driver_alarm' and e[2]==600)
        metadata=next(i for i,e in enumerate(h.events) if e[0]=='driver_metadata')
        persistence=next(i for i,e in enumerate(h.events) if e[0]=='post_cleanup_fsync')
        self.assertLess(arm,metadata);self.assertLess(metadata,persistence)
        self.assertEqual(h.cleanup_deadlines,[1905.0])
        self.assertFalse(result['phase_accounting_complete'])
        self.assertEqual(self.sidecars()[-1]['preservation_deadline_monotonic'],2500.0)
        self.assertEqual(len(self.sidecars()),1)

    def test_R1D08_reconciliation_expiry_has_one_reserved_marker(self):
        def first_failure(*a,**k):self.now=1900.0;raise c.IntegrityError('fixed first integrity failure')
        def expired_reconciliation(root):self.now=2601.0;raise d.PreservationExpired()
        inventory=c.Budget.inventory
        def bounded_inventory(budget):
            self.assertLess(self.now,2500.0,'ordinary full inventory after expiry')
            return inventory(budget)
        with self.patches(),patch.object(d,'verify_files',side_effect=first_failure), \
                patch.object(d,'reconcile_prefix',side_effect=expired_reconciliation) as reconcile, \
                patch.object(c.Budget,'inventory',bounded_inventory),patch.object(d,'recovery_inventory') as recovery, \
                patch.object(transport,'package_attempt') as package,patch.object(d,'write_failure_receipt',wraps=d.write_failure_receipt) as reserved:
            self.assertEqual(self.run_measure(),1)
        reconcile.assert_called_once();reserved.assert_called_once();recovery.assert_not_called();package.assert_not_called()
        marker=self.sidecars()[0]
        self.assertEqual(marker['failure']['error'],'fixed first integrity failure')
        self.assertEqual(marker['preservation_deadline_monotonic'],2500.0)
        self.assertTrue(any(e['status']=='resource_incomplete' for e in marker['secondary_errors']))

    def test_R1D09_publication_expiry_retains_discovered_integrity_and_counts(self):
        for kind in ('write_expiry','read_expiry','write_integrity_at_expiry'):
            with self.subTest(kind=kind):
                self.new_attempt('discovered-'+kind);self.now=1000.0
                earlier=c.error_record(c.IntegrityError('fixed discovered retained mismatch'),'cell_measurement')
                counts={'actual_starts':2,'actual_starts_upper_bound':2,'pre_call_markers':2,'actual_returns':1,
                    'confirmed_captures':1,'capture_gaps':[{'literal':'uncaptured second return'}],
                    'corrupt_evidence':[],'unavailable_evidence':[],
                    'retained_failures':[earlier] if kind=='write_expiry' else []}
                original=c.Budget.write;actual_read=d._prefix_read;failed=[];reconciled=[];receipt_reads=[]
                def first_failure(*a,**k):
                    self.now=1900.0
                    if kind=='read_expiry':c.update_receipt(self.attempt,status='integrity_invalid',failure=earlier)
                    raise OSError('fixed initially observed IO')
                def reconcile(root):reconciled.append(True);return counts
                def read(root,path,*a,**k):
                    result=actual_read(root,path,*a,**k)
                    if Path(path).name=='receipt.json':
                        receipt_reads.append(True)
                        if kind=='read_expiry':self.now=2500.0
                    return result
                def write(budget,path,value,**kwargs):
                    if reconciled and Path(path).name=='receipt.json' and value.get('failure'):
                        failed.append(True);self.now=2500.0
                        if kind=='write_integrity_at_expiry':raise c.IntegrityError('fixed terminal publication contradiction')
                        raise d.PreservationExpired()
                    return original(budget,path,value,**kwargs)
                with self.patches(),patch.object(d,'verify_files',side_effect=first_failure), \
                        patch.object(d,'reconcile_prefix',side_effect=reconcile) as reconciliation, \
                        patch.object(d,'_prefix_read',side_effect=read),patch.object(c.Budget,'write',write), \
                        patch.object(d,'write_failure_receipt',wraps=d.write_failure_receipt) as reserved, \
                        patch.object(transport,'package_attempt') as package:
                    self.assertEqual(self.run_measure(),1)
                reconciliation.assert_called_once();reserved.assert_called_once();package.assert_not_called()
                self.assertEqual(failed,[] if kind=='read_expiry' else [True]);self.assertEqual(receipt_reads,[True])
                marker=self.sidecars()[0]
                self.assertEqual(marker['failure']['error'],'fixed terminal publication contradiction'
                    if kind=='write_integrity_at_expiry' else 'fixed discovered retained mismatch')
                self.assertEqual(marker['status'],'integrity_invalid')
                self.assertEqual((marker['actual_starts'],marker['actual_returns'],marker['confirmed_captures']),(2,1,1))
                self.assertEqual(marker['count_evidence'],'last_available_reconciliation')
                self.assertEqual(marker['preservation_deadline_monotonic'],2500.0)
                self.assertTrue(any(e['status']=='resource_incomplete' for e in marker['secondary_errors']))

    def test_R1D10_unconfirmed_arm_never_retries_or_starts_bulk(self):
        for kind in ('before','after','shorter_anchor'):
            with self.subTest(kind=kind):
                self.new_attempt('arm-'+kind);attempts=[]
                original=self.timers.setitimer
                def timer(which,seconds,interval=0):
                    attempts.append(seconds)
                    failing=seconds==(100 if kind=='shorter_anchor' else 600)
                    if failing and kind!='after':raise OSError('literal timer arm failed before operation')
                    result=original(which,seconds,interval)
                    if failing:raise MemoryError('literal timer arm failed after operation')
                    return result
                with patch.object(d.signal,'setitimer',side_effect=timer),patch.object(d,'reconcile_prefix') as reconcile, \
                        patch.object(d,'terminalize') as terminal,patch.object(transport,'package_attempt') as package:
                    if kind=='shorter_anchor':
                        self.now=400.0;self.make_receipt()
                        with patch.object(d,'recover_closing_anchor',return_value={'preservation_deadline_monotonic':500.0}), \
                                patch.object(c.Budget,'write') as ordinary,patch.object(d,'recovery_inventory') as inventory:
                            self.assertEqual(self.run_preserve('1000000'),1)
                        ordinary.assert_not_called();inventory.assert_not_called()
                    else:
                        self.now=1900.0
                        with self.patches(),patch.object(d,'verify_files',side_effect=c.IntegrityError('fixed earlier mismatch')):
                            self.assertEqual(self.run_measure(),1)
                reconcile.assert_not_called();terminal.assert_not_called();package.assert_not_called()
                self.assertEqual(attempts,[600.0,100.0,0] if kind=='shorter_anchor' else [1800,600.0,0])
                self.assertEqual(self.sidecars()[-1]['preservation_deadline_monotonic'],500.0 if kind=='shorter_anchor' else 2500.0)
                self.assertEqual(len(self.sidecars()),1)

    def test_R1D11_callback_metadata_or_missing_timestamp_cannot_renew(self):
        retained=d._retained_failures
        for kind in ('metadata','missing_timestamp'):
            with self.subTest(kind=kind):
                self.new_attempt('callback-'+kind);self.now=1000.0
                def retain(value,path):
                    if path=='first_supervisor_failure' and kind=='metadata':
                        self.assertIn(('timer',1900.0,600.0),self.timers.events)
                        raise MemoryError('literal callback metadata allocation')
                    return retained(value,path)
                def child(*a,**k):
                    global STUB_SUPERVISOR_INVOCATIONS
                    STUB_SUPERVISOR_INVOCATIONS+=1;self.now=1900.0
                    observed={'status':'resource_incomplete','reason':'fixed first resource failure','exit_code':None}
                    if kind=='metadata':observed['first_failure_monotonic']=1900.0
                    try:
                        return k['on_terminal_failure'](observed)
                    except BaseException:
                        if kind=='metadata':self.now=2601.0
                        raise
                with self.patches(),patch.object(supervision,'run_child',side_effect=child) as run, \
                        patch.object(d,'_retained_failures',side_effect=retain),patch.object(d,'reconcile_prefix') as reconcile, \
                        patch.object(d,'publish_preservation_handoff') as handoff:
                    self.assertEqual(self.run_measure(),1)
                run.assert_called_once();reconcile.assert_not_called();handoff.assert_not_called()
                self.assertEqual([e[2] for e in self.timers.events if e[0]=='timer' and e[2]>0],
                    [1800,600.0] if kind=='metadata' else [1800])
                self.assertEqual(self.sidecars()[-1]['preservation_deadline_monotonic'],2500.0 if kind=='metadata' else None)
                self.assertEqual(len(self.sidecars()),1)

    def assert_restoration_matrix_result(self, case, marker):
        last=self.timers.events[-4:]
        self.assertEqual([event[0] for event in last],['timer','handler','get_timer','get_handler'])
        self.assertEqual(last[0][2],0);self.assertIs(last[1][2],True)
        restoration=[item for item in (marker['failure'],*marker['secondary_errors']) if 'restoration_confirmed' in item]
        self.assertTrue(restoration)
        confirmed=case in ('disable_after_memory','handler_after_memory')
        self.assertTrue(all(item['restoration_confirmed'] is confirmed for item in restoration))
        if confirmed:self.assertTrue(all(item['status']=='resource_incomplete' for item in restoration))
        else:self.assertTrue(any(item['status']=='integrity_invalid' for item in restoration))

    def test_R1D12_coordinator_restoration_independent_confirmation_matrix(self):
        for case in RESTORATION_CASES:
            with self.subTest(case=case):
                self.new_attempt('coordinator-'+case);self.timers.case=case
                with self.patches(),patch.object(supervision,'run_child',side_effect=self.fake_child), \
                        patch.object(d,'terminalize',wraps=d.terminalize) as terminal:
                    self.assertEqual(self.run_measure(),1)
                terminal.assert_not_called();self.assertEqual(len(self.sidecars()),1)
                self.assertEqual(self.read_receipt()['status'],'execution_complete')
                marker=self.sidecars()[0];self.assert_restoration_matrix_result(case,marker)
                self.assertEqual(marker['status'],'resource_incomplete' if case.endswith('after_memory') else 'integrity_invalid')

    def test_R1D13_offline_restoration_only_sidecar_preserves_in_memory_integrity(self):
        earlier=c.error_record(c.IntegrityError('fixed in-memory offline integrity'),'offline_verification')
        for case in RESTORATION_CASES:
            with self.subTest(case=case):
                self.new_attempt('offline-'+case);self.make_receipt('measuring');self.timers.case=case
                original=(self.attempt/'receipt.json').read_bytes()
                def offline(*args,**kwargs):kwargs['failure_state']['primary']=earlier;return 0
                with patch.object(d,'_preserve',side_effect=offline) as bulk, \
                        patch.object(d,'terminalize') as terminal,patch.object(c.Budget,'write') as ordinary, \
                        patch.object(d,'reconcile_prefix') as reconcile,patch.object(d,'write_failure_receipt',wraps=d.write_failure_receipt) as reserved:
                    self.assertEqual(self.run_preserve(),1)
                bulk.assert_called_once();reserved.assert_called_once()
                for call in (terminal,ordinary,reconcile):call.assert_not_called()
                self.assertEqual((self.attempt/'receipt.json').read_bytes(),original)
                marker=self.sidecars()[0];self.assert_restoration_matrix_result(case,marker)
                self.assertEqual(marker['failure']['error'],'fixed in-memory offline integrity')
                self.assertEqual(marker['status'],'integrity_invalid')

    def test_R1D14_handler_mutation_then_error_still_restores_owned_state(self):
        for mode in ('coordinator','offline'):
            with self.subTest(mode=mode):
                self.new_attempt('handler-'+mode)
                if mode=='offline':self.make_receipt('measuring')
                original=self.timers.signal;installed=[]
                def handler(number,value):
                    result=original(number,value)
                    if value is not self.timers.old:
                        installed.append(value);raise MemoryError('literal handler allocation after mutation')
                    return result
                with patch.object(d.signal,'signal',side_effect=handler),patch.object(d,'_preserve') as bulk:
                    if mode=='coordinator':
                        with self.patches():self.assertEqual(self.run_measure(),1)
                    else:self.assertEqual(self.run_preserve(),1)
                bulk.assert_not_called();self.assertEqual(len(installed),1)
                self.assertIs(self.timers.handler,self.timers.old);self.assertEqual(self.timers.timer,(0.0,0.0))
                self.assertEqual([e[0] for e in self.timers.events[-4:]],['timer','handler','get_timer','get_handler'])
                self.assertFalse(any(e[0]=='timer' and e[2]>0 for e in self.timers.events))
                self.assertEqual(len(self.sidecars()),1);self.assertEqual(self.sidecars()[0]['status'],'resource_incomplete')

    def test_R1D15_expiry_before_or_during_verification_stops_optional_work(self):
        for kind in ('incoming_expired','verification_expired'):
            with self.subTest(kind=kind):
                self.root=self.root/kind;self.root.mkdir();self.attempt=self.root/'attempt';self.now=1000.0
                self.make_receipt();before=(self.attempt/'receipt.json').read_bytes()
                self.timers.events.clear();self.timers.restoring=False
                def verify(*a,**k):self.now=1601.0;raise d.PreservationExpired()
                with patch.object(verification,'verify_attempt',side_effect=verify) as verification_call, \
                        patch.object(d,'reconcile_prefix') as reconcile,patch.object(d,'recovery_inventory') as inventory, \
                        patch.object(c.Budget,'inventory') as full_inventory,patch.object(transport,'package_attempt') as package:
                    self.assertEqual(self.run_preserve('999000' if kind=='incoming_expired' else '1600000'),1)
                for call in (reconcile,inventory,full_inventory,package):call.assert_not_called()
                self.assertEqual(verification_call.call_count,0 if kind=='incoming_expired' else 1)
                self.assertEqual((self.attempt/'receipt.json').read_bytes(),before)
                self.assertEqual(len(self.sidecars()),1)
                self.assertEqual(self.sidecars()[0]['status'],'resource_incomplete')
                self.assertFalse((self.root/'transport').exists())
                self.assertFalse(any(e[0]=='timer' and e[1]>=1600 and e[2]>0 for e in self.timers.events))

        with self.subTest(kind='second_retain_expiry_preserves_secondary_causes'):
            self.root=self.root/'second-retain';self.root.mkdir();self.attempt=self.root/'attempt';self.now=1000.0
            self.make_receipt();self.timers.events.clear();self.timers.restoring=False
            old_secondary=c.error_record(OSError('fixed previously observed secondary'),'offline_verification')
            primary=c.IntegrityError('fixed original offline integrity')
            primary.worker36_secondary_errors=[old_secondary]
            actual_reconcile=d.reconcile_prefix;actual_write=c.Budget.write;reconciliations=[]
            def reconcile(root):
                reconciliations.append(True)
                if len(reconciliations)==2:self.now=1601.0;raise d.PreservationExpired()
                return actual_reconcile(root)
            def write(budget,path,value,**kwargs):
                if Path(path).name=='verification-gate-failure.json':raise OSError('fixed later gate persistence')
                return actual_write(budget,path,value,**kwargs)
            with patch.object(verification,'verify_attempt',side_effect=primary), \
                    patch.object(d,'reconcile_prefix',side_effect=reconcile),patch.object(c.Budget,'write',write), \
                    patch.object(d,'recovery_inventory') as inventory,patch.object(transport,'package_attempt') as package:
                self.assertEqual(self.run_preserve(),1)
            self.assertEqual(reconciliations,[True,True]);inventory.assert_not_called();package.assert_not_called()
            self.assertEqual(len(self.sidecars()),1);marker=self.sidecars()[0]
            self.assertEqual(marker['failure']['error'],'fixed original offline integrity')
            errors={item['error'] for item in marker['secondary_errors']}
            self.assertIn('fixed previously observed secondary',errors)
            self.assertIn('fixed later gate persistence',errors)
            self.assertTrue(any(item['status']=='resource_incomplete' for item in marker['secondary_errors']))
            self.assertEqual(marker['preservation_deadline_monotonic'],1600.0)

    def test_R1D16_partial_spawn_failure_stops_before_second_cell(self):
        for known in (True,False):
            with self.subTest(known=known):
                self.new_attempt('partial-'+str(known));self.now=1000.0
                status='resource_incomplete' if known else 'execution_incomplete'
                result={'schema':'worker36.supervision.v1','status':status,'reason':'literal partial Popen failure',
                    'exit_code':None,'spawn_attempted':True,'spawn_initialization_complete':False,
                    'spawn_ownership_uncertain':not known,'spawned':known,'pid':987654321 if known else None,
                    'child_accounting_complete':False,'phase_accounting_complete':False,
                    'primary_outcome':{'status':status,'reason':'literal partial Popen failure'},
                    'preservation_transition_attempted':True,'preservation_transition_complete':True,
                    'preservation_deadline_monotonic':2500.0,'secondary_failures':[]}
                def child(*a,**k):
                    self.now=1900.0
                    deadline=k['on_terminal_failure']({'status':status,'reason':'literal partial Popen failure',
                        'first_failure_monotonic':1900.0,'exit_code':None})
                    self.assertEqual(deadline,2500.0)
                    return self.supervisor_result(copy.deepcopy(result))
                with self.patches(),patch.object(d,'SCHEDULE',(FAKE_CELL,{**FAKE_CELL,'cell':2})), \
                        patch.object(supervision,'run_child',side_effect=child) as run:
                    self.assertEqual(self.run_measure(),1)
                run.assert_called_once();self.assertFalse((self.attempt/'cells/02').exists())
                receipt=self.read_receipt();self.assertEqual(receipt['status'],status)
                self.assertEqual(receipt['completed_prefix'],[])
                self.assertEqual((receipt['actual_starts'],receipt['actual_starts_upper_bound']),(0,0))
                retained=c.strict_json((self.attempt/'supervisor-cell-01.json').read_bytes())
                self.assertIs(retained['spawn_ownership_uncertain'],not known)
                self.assertFalse(retained['phase_accounting_complete'])
                self.assertFalse((self.attempt/'measurement-phase-close.json').exists())

if __name__=='__main__':unittest.main()
