"""D01–D54: fixed literal orchestration faults, never historical policy code."""
from contextlib import ExitStack
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

class DriverIntegration(unittest.TestCase):
    def setUp(self):
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
        self.prov={'workflow_run':'123','workflow_attempt':'1','attempt_path':str(self.attempt),'durable_root':str(self.root)}
    def patches(self):
        stack=ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(patch.object(d,'ROOT',self.root));stack.enter_context(patch.object(d,'EXPERIMENT',self.experiment))
        stack.enter_context(patch.object(d,'TEST_RECEIPT',self.test_receipt));stack.enter_context(patch.object(d,'SCHEDULE',(FAKE_CELL,)))
        stack.enter_context(patch.dict(os.environ,{'WORKER36_CLAIM_DIRECTORY':str(self.claim),'RUNNER_NAME':'bandido-alcatraz-ci','GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1'}))
        stack.enter_context(patch.object(d,'read_admission',return_value=(self.go,self.prov)))
        stack.enter_context(patch.object(d,'durable_location'))
        stack.enter_context(patch.object(d,'runtime_check',return_value={'literal':'runtime stub'}))
        stack.enter_context(patch.object(d,'install_memory_cap'))
        original_getrlimit=resource.getrlimit
        stack.enter_context(patch.object(resource,'getrlimit',side_effect=lambda kind:(-1,-1) if kind==resource.RLIMIT_AS else original_getrlimit(kind)))
        stack.enter_context(patch.object(d,'read_manifest',return_value={'files':[]}))
        stack.enter_context(patch.object(d,'restore',side_effect=lambda repo,target,manifest,budget:budget.mkdir(target)))
        stack.enter_context(patch.object(d,'verify_files'))
        return stack
    def run_measure(self):
        return d.measure(self.attempt,self.admission,c.sha(self.admission.read_bytes()),self.provenance,c.sha(self.provenance.read_bytes()))
    def supervisor_result(self,value):
        global STUB_SUPERVISOR_INVOCATIONS
        STUB_SUPERVISOR_INVOCATIONS+=1
        return value
    def read_receipt(self):return c.strict_json((self.attempt/'receipt.json').read_bytes())
    def make_receipt(self,status='execution_complete'):
        self.attempt.mkdir();c.Budget(self.attempt).write(self.attempt/'receipt.json',{'schema':'worker36-attempt-v1','status':status,'failure':None,'actual_starts':0,'phase':'verification_pending',
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
        with patch.object(d,'install_memory_cap'),patch.object(verification,'verify_attempt',side_effect=c.IntegrityError('fixed offline mismatch')),patch.object(transport,'package_attempt',side_effect=package_effect):
            return d.preserve(self.attempt,self.root/'transport',self.root/'verification.json',self.root/'recovery.json',
                admission=self.admission,admission_sha256=c.sha(self.admission.read_bytes()),admission_provenance=self.provenance,
                admission_provenance_sha256=c.sha(self.provenance.read_bytes()),expected_head='a'*40,expected_tree='b'*40,expected_workflow_run='123')
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
        repo=self.root/'repo';repo.mkdir();path=repo/'experiments/synthetic-profile-overhead/focused-sixth-repair-test-receipt.json';path.parent.mkdir(parents=True)
        source=repo/'literal.py';source.write_bytes(b'# fixed source stub\n')
        record={'success':True,'failures':0,'errors':0,'candidate_evaluator_calls':0,'reference_evaluator_calls':0,'games':0,'measurement_fixture_constructions':0,'historical_source_imports':0,'checked_file_sha256':{'literal.py':c.sha(source.read_bytes())}}
        path.write_bytes(c.canonical(record));pin=c.sha(path.read_bytes())
        with patch.object(d,'checked_source_paths',return_value={'literal.py'}):
            d.verify_test_receipt(repo,pin)
            with self.assertRaises(c.IntegrityError):d.verify_test_receipt(repo,'0'*64)
            source.write_bytes(b'# changed\n')
            with self.assertRaises(c.IntegrityError):d.verify_test_receipt(repo,pin)
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
        original=d.signal.signal;old=d.signal.getsignal(d.signal.SIGALRM);failed=[]
        def restoration(number,handler):
            value=original(number,handler)
            if handler==old and not failed:
                failed.append(True);raise MemoryError('restoration memory after actual restore')
            return value
        with self.patches(),patch.object(supervision,'run_child',side_effect=self.fake_child),patch.object(d.signal,'signal',restoration):
            self.assertEqual(self.run_measure(),1)
        self.assertEqual(self.read_receipt()['status'],'resource_incomplete')
    def test_D45_shared_preservation_deadline(self):
        self.make_receipt();start=time.monotonic()-701;self.write_closing_proof(preservation_started_monotonic=start,preservation_deadline_monotonic=start+600)
        captured=[]
        with patch.object(d,'install_memory_cap'),patch.object(verification,'verify_attempt') as verify,patch.object(transport,'package_attempt',side_effect=lambda *a,**k:(captured.append(k['deadline_monotonic']) or {'status':'blocked'})):
            self.assertEqual(d.preserve(self.attempt,self.root/'transport',self.root/'verification.json',self.root/'recovery.json',admission=self.admission,admission_sha256='0'*64,admission_provenance=self.provenance,admission_provenance_sha256='1'*64,expected_head='a'*40,expected_tree='b'*40,expected_workflow_run='123'),1)
        verify.assert_not_called();self.assertEqual(captured,[start+600]);self.assertEqual(self.read_receipt()['status'],'resource_incomplete')
    def test_D46_closing_proof_required(self):
        self.make_receipt();proof=verification.closing_phase(self.attempt,self.read_receipt())
        self.assertEqual(proof['computational_receipt']['sha256'],c.file_info(self.attempt/'receipt.json')['sha256'])
        (self.attempt/'measurement-phase-close.json').unlink()
        self.assertEqual(self.preservation(lambda *a,**k:{'status':'packaged'}),1)
        self.assertEqual(self.read_receipt()['status'],'execution_incomplete')

    def preserve_recording_deadline(self):
        captured=[]
        with patch.object(d,'install_memory_cap'),patch.object(verification,'verify_attempt') as verify,patch.object(transport,'package_attempt',side_effect=lambda *a,**k:(captured.append(k['deadline_monotonic']) or {'status':'blocked'})):
            code=d.preserve(self.attempt,self.root/'transport',self.root/'verification.json',self.root/'recovery.json',admission=self.admission,admission_sha256='0'*64,admission_provenance=self.provenance,admission_provenance_sha256='1'*64,expected_head='a'*40,expected_tree='b'*40,expected_workflow_run='123')
        verify.assert_not_called();self.assertEqual(code,1)
        return captured
    def test_D47_terminal_status_preserves_closing_deadline(self):
        self.make_receipt();start=time.monotonic()-701;self.write_closing_proof(preservation_started_monotonic=start,preservation_deadline_monotonic=start+600)
        anchor=(self.attempt/'measurement-phase-close.json').read_bytes()
        d.terminalize(self.attempt,c.error_record(MemoryError('later restoration resource failure'),'timer_restoration'))
        self.assertNotEqual(c.file_info(self.attempt/'receipt.json')['sha256'],c.strict_json(anchor)['computational_receipt']['sha256'])
        self.assertEqual(self.preserve_recording_deadline(),[start+600]);self.assertEqual(self.read_receipt()['status'],'resource_incomplete')
        self.assertEqual((self.attempt/'measurement-phase-close.json').read_bytes(),anchor)
    def test_D48_malformed_receipt_keeps_closing_deadline(self):
        self.make_receipt();start=time.monotonic()-701;self.write_closing_proof(preservation_started_monotonic=start,preservation_deadline_monotonic=start+600)
        anchor=(self.attempt/'measurement-phase-close.json').read_bytes();(self.attempt/'receipt.json').write_bytes(b'{committed malformed receipt')
        self.assertEqual(self.preserve_recording_deadline(),[start+600])
        self.assertEqual((self.attempt/'receipt.json').read_bytes(),b'{committed malformed receipt')
        self.assertEqual((self.attempt/'measurement-phase-close.json').read_bytes(),anchor)
        sidecars=[c.strict_json(p.read_bytes()) for p in self.attempt.glob('failure-receipt-parent-*.json')]
        self.assertTrue(sidecars);self.assertTrue(all(x['status']=='integrity_invalid' for x in sidecars))

    def test_D49_unrecoverable_anchor_never_renews_budget(self):
        original=Path.read_bytes
        for index,fault in enumerate(('denied','malformed')):
            with self.subTest(fault=fault):
                self.root=self.root/('anchor-'+str(index));self.root.mkdir();self.attempt=self.root/'attempt'
                self.make_receipt();path=self.attempt/'measurement-phase-close.json'
                if fault=='malformed':path.write_bytes(b'{bad closing proof')
                def read(target):
                    if target==path and fault=='denied':raise PermissionError('closing anchor unavailable')
                    return original(target)
                with patch.object(Path,'read_bytes',read):deadlines=self.preserve_recording_deadline()
                self.assertEqual(len(deadlines),1);self.assertLessEqual(deadlines[0],time.monotonic())

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
                self.assertEqual(self.preserve_recording_deadline(),[start+600])
                self.assertEqual(staged.read_bytes(),raw);self.assertFalse(final.exists())
                self.assertEqual(self.read_receipt()['status'],'resource_incomplete' if age==701 else 'execution_incomplete')

    def test_D52_missing_anchor_after_possible_completion(self):
        for index,kind in enumerate(('complete','terminalized','missing-receipt')):
            with self.subTest(kind=kind):
                self.root=self.root/('missing-'+str(index));self.root.mkdir();self.attempt=self.root/'attempt';self.make_receipt()
                (self.attempt/'measurement-phase-close.json').unlink()
                if kind=='terminalized':d.terminalize(self.attempt,c.error_record(OSError('later restoration failure'),'coordinator_timer_restoration'))
                if kind=='missing-receipt':(self.attempt/'receipt.json').unlink()
                raw=self.attempt/'fixed-prefix.bin';raw.write_bytes(b'literal surviving evidence')
                # Exercise real bounded transport once: an unknown anchor must
                # be rejected before destination creation, not just reported.
                if kind=='complete':
                    captured=[];actual=transport.package_attempt
                    def package(*a,**k):captured.append(k['deadline_monotonic']);return actual(*a,**k)
                    with patch.object(d,'install_memory_cap'),patch.object(verification,'verify_attempt') as verify,patch.object(transport,'package_attempt',side_effect=package):
                        code=d.preserve(self.attempt,self.root/'transport',self.root/'verification.json',self.root/'recovery.json',admission=self.admission,admission_sha256='0'*64,admission_provenance=self.provenance,admission_provenance_sha256='1'*64,expected_head='a'*40,expected_tree='b'*40,expected_workflow_run='123')
                    verify.assert_not_called();self.assertEqual(code,1);deadlines=captured
                    self.assertFalse((self.root/'transport').exists())
                else:deadlines=self.preserve_recording_deadline()
                self.assertEqual(len(deadlines),1);self.assertLessEqual(deadlines[0],time.monotonic())
                self.assertEqual(raw.read_bytes(),b'literal surviving evidence')
                terminal=([self.read_receipt()] if kind!='missing-receipt' else
                    [c.strict_json(p.read_bytes()) for p in self.attempt.glob('failure-receipt-parent-*.json')])
                self.assertTrue(terminal);self.assertTrue(all(x['status']=='execution_incomplete' for x in terminal))
                recovery=c.strict_json((self.root/'recovery.json').read_bytes())
                self.assertFalse(recovery['retained_inventory']['inventory_complete'])

    def test_D53_torn_or_future_staged_anchor_is_uncertain(self):
        for index,kind in enumerate(('torn','future')):
            with self.subTest(kind=kind):
                self.root=self.root/('uncertain-'+str(index));self.root.mkdir();self.attempt=self.root/'attempt';self.make_receipt()
                if kind=='future':
                    start=time.monotonic()+100;self.write_closing_proof(preservation_started_monotonic=start,preservation_deadline_monotonic=start+600)
                final=self.attempt/'measurement-phase-close.json';staged=final.with_name(final.name+'.tmp');final.rename(staged)
                if kind=='torn':staged.write_bytes(b'{uncommitted partial anchor')
                raw=staged.read_bytes();deadlines=self.preserve_recording_deadline()
                self.assertLessEqual(deadlines[0],time.monotonic());self.assertEqual(staged.read_bytes(),raw)
                self.assertEqual(self.read_receipt()['status'],'execution_incomplete')

    def test_D54_positive_preclosing_evidence_only(self):
        cases=(('execution_blocked','admission',False),('measuring','measurement',False),('measuring','measurement',True))
        for index,(status,phase,staging) in enumerate(cases):
            with self.subTest(status=status,phase=phase,staging=staging):
                self.root=self.root/('preclosing-'+str(index));self.root.mkdir();self.attempt=self.root/'attempt';self.make_receipt(status)
                path=self.attempt/'receipt.json';value=self.read_receipt();value.update(phase=phase,completed_prefix=[])
                path.write_bytes(c.canonical(value))
                if status=='measuring':d.terminalize(self.attempt,c.error_record(OSError('partial cell unavailable'),'measurement'))
                if staging:(self.attempt/'receipt.json.tmp').write_bytes(b'{possible computational publication')
                before=time.monotonic();deadlines=self.preserve_recording_deadline();after=time.monotonic()
                self.assertEqual(len(deadlines),1)
                if staging:self.assertLessEqual(deadlines[0],after)
                else:self.assertGreaterEqual(deadlines[0],before+599);self.assertLessEqual(deadlines[0],after+600)

if __name__=='__main__':unittest.main()
