"""Convert static-analyzer log lines into GitHub workflow-log annotations.

Emits `::error`/`::warning` commands (GitHub renders these as inline PR
annotations). Understands both mypy and pyright line formats:

    mypy:    absbox/client.py:25: error: Message
    pyright: absbox/client.py:25:4 - error: Message

Usage: python tools/annotate_from_log.py <log_path> <title> [max_entries]
"""
import re
import sys

_LINE = re.compile(r"^(?P<file>.+?):(?P<lno>\d+):(?:\d+)?[ \t-]*(?P<sev>error|warning): (?P<msg>.*)$")


def annotate(log_path: str, title: str, max_entries: int = 200) -> int:
    """Print workflow-log annotation commands for finding lines; returns count."""
    n = 0
    with open(log_path, encoding='utf-8', errors='replace') as logf:
        for line in logf:
            if n >= max_entries:
                break
            m = _LINE.match(line.rstrip('\n'))
            if not m:
                continue
            f = m['file']
            lno = m['lno']
            sev = m['sev']
            text = (m['msg'].splitlines() or [''])[0][:160]
            print(f'::{sev} file={f},line={lno},endLine={lno},title={title}::{text}', flush=True)
            n += 1
    return n


if __name__ == '__main__':
    path = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else 'static analysis'
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    annotate(path, title, limit)
