"""Explicit Worker36 commands only. No default measurement or admission."""
from worker36.driver import main

if __name__ == '__main__':
    raise SystemExit(main())
