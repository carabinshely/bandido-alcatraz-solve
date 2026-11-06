"""Import only completed aggregate results and frozen policy bytes for the guide."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent / 'var/orchestrator'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report_path = EVIDENCE / 'bandido-consolidated-pause-report-20261106.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    sources = {
        110: ('local110-final-summary-20261104.json', 'local92_early_exit_policy.py', 'EarlyExitPolicy', 'Ранний спокойный выход', '2026-11-04'),
        113: ('local113-final-summary-20261104.json', 'local67_post_exit_closure_policy.py', 'PostExitClosurePolicy', 'Закрывать тоннели после выхода', '2026-11-04'),
        127: ('local127-b1-summary-20261105.json', 'local127_joint_cleanup_policy.py', 'JointCleanupPolicy', 'Общая оценка оставшейся работы', '2026-11-05'),
        129: ('local129-b1-summary-20261106.json', 'local129_port_cleanup_policy.py', 'JointCleanupPolicy', 'Учитывать входы возле воды', '2026-11-06'),
    }
    result = []
    target = HERE / 'inputs/research-code'
    target.mkdir(parents=True, exist_ok=True)
    pins = {row['strategy']: row['summary_sha256'] for row in report['previous_results']}
    pins[129] = report['provenance']['summary_sha256']
    for number, (summary_name, code_name, class_name, name, date) in sources.items():
        path = EVIDENCE / summary_name
        assert digest(path) == pins[number], summary_name
        summary = json.loads(path.read_text(encoding='utf-8'))
        code = EVIDENCE / code_name
        assert digest(code) == summary['policy_sha256'], code_name
        assert summary['wins_candidate'] == summary['both_win'] + summary['only_candidate_win']
        assert summary['wins_control'] == summary['both_win'] + summary['only_control_win']
        assert summary['pairs'] == sum(summary[k] for k in ('both_win', 'neither_win', 'only_candidate_win', 'only_control_win'))
        (target / (code_name + '.txt')).write_bytes(code.read_bytes())
        fields = ('study_id', 'pairs', 'wins_candidate', 'wins_control', 'both_win', 'neither_win',
                  'only_candidate_win', 'only_control_win', 'paired_win_difference',
                  'paired_risk_difference_95pct_interval', 'exact_two_sided_discordant_p',
                  'primary_positive_superiority', 'policy_sha256', 'source_head', 'source_manifest_sha256', 'seeds')
        row = {key: summary[key] for key in fields if key in summary}
        row.update(number=number, date=date, name=name, class_name=class_name,
                   code_file=code_name + '.txt', source_summary=summary_name,
                   source_summary_sha256=digest(path), adopted=False,
                   control_policy_sha256=summary.get('control_policy_sha256', summary.get('baseline_sha256', report['provenance']['baseline_sha256'])))
        result.append(row)
    baseline = EVIDENCE / 'local92_catalog_baseline.py'
    assert digest(baseline) == report['provenance']['baseline_sha256']
    (target / 'local92_catalog_baseline.py.txt').write_bytes(baseline.read_bytes())
    document = dict(schema='guide-recent-completed-results-v1', as_of='2026-11-06',
                    ruleset='v2-exact-equipment-quota-limited-collect-full-hand-refresh',
                    hand_size=6, consolidation_sha256=digest(report_path),
                    data_scope='Aggregate results and frozen policy text only; private raw traces and operational records excluded.',
                    studies=result)
    (HERE / 'inputs/recent-research.json').write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Imported four completed studies; source-summary and frozen-policy SHA-256 checks passed.')


if __name__ == '__main__':
    main()
