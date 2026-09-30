"""Synthetic checkout/retry evidence retention; no research execution."""
import subprocess
import tempfile
import unittest
from pathlib import Path

class WorkflowRetentionTests(unittest.TestCase):
    def test_output_paths_survive_checkout_clean_and_new_attempt(self):
        workflow=(Path(__file__).resolve().parents[1]/'.github/workflows/worker28.yml').read_text()
        prefix='${{ github.workspace }}/../bandido-worker28-evidence/${{ github.run_id }}/${{ github.run_attempt }}/'
        self.assertEqual(workflow.count('W28_OUTPUT: '+prefix),2)
        self.assertEqual(workflow.count('--output "$W28_OUTPUT"'),4)
        self.assertEqual(workflow.count('path: ${{ env.W28_OUTPUT }}/'),2)
        self.assertNotIn('--output artifacts/tmp',workflow)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); checkout=root/'repo';checkout.mkdir()
            subprocess.run(['git','init','-q',str(checkout)],check=True)
            old=root/'bandido-worker28-evidence'/'123'/'1'/'shard-0';old.mkdir(parents=True)
            receipt=old/'receipt.json';receipt.write_bytes(b'{"status":"running"}')
            subprocess.run(['git','clean','-ffdx'],cwd=checkout,check=True,capture_output=True)
            new=root/'bandido-worker28-evidence'/'123'/'2'/'shard-0';new.mkdir(parents=True)
            (new/'receipt.json').write_bytes(b'{"status":"complete"}')
            self.assertEqual(receipt.read_bytes(),b'{"status":"running"}')

if __name__=='__main__':unittest.main()
