"""Production entrypoint.

Runs three steps in sequence and replaces the process with uvicorn:

  1. Print a one-line boot diagnostic showing how ``LIP_DATABASE_URL``
     was parsed (scheme, host, port, database). Password is never
     printed. This is the first signal you have that the secret was
     set correctly inside the container.
  2. ``alembic upgrade head`` against the live DB.
  3. ``exec uvicorn lip.api.main:app --host 0.0.0.0 --port $PORT``.

Used as the container ``CMD`` so it survives every deploy.
"""

from __future__ import annotations

import os
import sys
import urllib.parse


def _print_db_diagnostic() -> None:
    raw = os.environ.get("LIP_DATABASE_URL", "")
    if not raw:
        print("[boot] LIP_DATABASE_URL is unset — app will fall back to localhost", flush=True)
        return

    # Detect the classic copy-paste mistake: shell-style quoting around
    # the secret value when pasted into a web form.
    stripped = raw.strip()
    if stripped != raw or stripped.startswith(("'", '"')) or stripped.endswith(("'", '"')):
        print(
            "[boot] LIP_DATABASE_URL looks quoted or whitespace-wrapped — "
            "re-save the secret without surrounding quotes",
            flush=True,
        )

    try:
        u = urllib.parse.urlparse(raw)
    except Exception as e:
        print(f"[boot] LIP_DATABASE_URL parse failed: {e!r}", flush=True)
        return

    print(
        "[boot] db "
        f"scheme={u.scheme!r} "
        f"host={u.hostname!r} "
        f"port={u.port} "
        f"db={u.path.lstrip('/')!r}",
        flush=True,
    )


def main() -> int:
    _print_db_diagnostic()

    # alembic
    rc = os.spawnvp(os.P_WAIT, "alembic", ["alembic", "upgrade", "head"])
    if rc != 0:
        print(f"[boot] alembic upgrade head failed with exit code {rc}", flush=True)
        return rc

    # exec replaces this process so uvicorn becomes PID 1's child.
    port = os.environ.get("PORT", "8080")
    os.execvp(
        "uvicorn",
        ["uvicorn", "lip.api.main:app", "--host", "0.0.0.0", "--port", port],
    )
    return 0  # unreachable


if __name__ == "__main__":
    sys.exit(main())
