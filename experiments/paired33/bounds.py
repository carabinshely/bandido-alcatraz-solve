"""Closed evidence budget for the separately admitted paired diagnostic."""
TERMINAL_RESERVE = 4 * 1024 * 1024


def decision_upper(public_bytes, roots, candidate):
    if (type(public_bytes) is not int or not 0 <= public_bytes <= 100000
            or type(roots) is not int or not 0 <= roots <= 32768
            or type(candidate) is not bool):
        raise ValueError('PROOF_BOUND_DOMAIN')
    # Fixed audited schema, bounded game integers/coordinates and ASCII keys.
    # Each science root+guard+five index tiers fits1024B; fixed fields fit16KiB.
    audits = 2 if candidate else 1
    return audits * (1024 * roots + 16384) + 2 * public_bytes + 65536


def reserve(used, upcoming, total):
    if any(type(x) is not int or x < 0 for x in (used, upcoming, total)):
        raise ValueError('PROOF_BOUND_DOMAIN')
    if used + upcoming + TERMINAL_RESERVE + 32 > total:
        raise ValueError('EVIDENCE_CAP_BEFORE_CALL_NO_TRUNCATION')


def reserve_records(used, upcoming, total):
    if any(type(x) is not int or x < 0 for x in (used, upcoming, total)):
        raise ValueError('PROOF_BOUND_DOMAIN')
    if used + upcoming > total:
        raise ValueError('RECORD_CAP_BEFORE_CALL_NO_TRUNCATION')
