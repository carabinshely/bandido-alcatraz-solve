"""Explicit Worker38 commands only. No default measurement or admission."""
from worker38.driver import main

if __name__ == '__main__':
    raise SystemExit(main())
