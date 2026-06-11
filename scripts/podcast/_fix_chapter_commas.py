"""One-off comma-spacing fixer kept for reference (vol-01 chapter cleanup).

Module-level argv access made this crash on bare import (it broke the
import-health sweep); the body now lives under a __main__ guard.
"""
import re
import sys


def main() -> None:
    p = sys.argv[1]
    s = open(p).read()
    s = re.sub(r',([A-Za-z])', r', \1', s)
    s = s.replace('in his earlier chapter on the four limits of the testimony',
                  'in his chapter on the four limits of the testimony')
    open(p, 'w').write(s)
    print('ok')


if __name__ == "__main__":
    main()
