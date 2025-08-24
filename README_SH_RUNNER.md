# Windows `.sh` Runner

This setup lets you double-click or open a `*.sh` file on Windows and have it executed correctly:

1. Run `source\install-sh-association.bat` once. This associates `.sh` files with `source\sh-runner.bat`.
2. Open any `.sh` file. The runner will:

   * Prefer WSL if installed.
   * Otherwise use Git Bash if found.
   * Otherwise fall back to a lightweight interpreter that supports simple lines like `uvicorn app:app --host 0.0.0.0 --port 8000`, `cd ...`, and `export VAR=value`.

The runner starts from the script’s directory so relative paths work. To pass arguments, open from a console using `script.sh arg1 arg2` after association.

Example `start_server.sh`:

```
uvicorn app:app --host 0.0.0.0 --port 8000
```

Double-click `start_server.sh` and it will run in a console. Ensure `uvicorn` is on your PATH or invoke it via `python -m uvicorn ...`.