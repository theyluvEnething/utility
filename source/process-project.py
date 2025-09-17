#!/usr/bin/env python3
import os
import sys
import time
import threading
import subprocess
import re
import importlib.util

DEBUG = True

SPIN_FRAMES = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']

def supports_ansi():
    try:
        if os.name == 'nt':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
        return True
    except Exception:
        return False

def c(text, code):
    return f"\033[{code}m{text}\033[0m" if supports_ansi() else text

def h1(text):
    bar = c("─" * max(20, len(text) + 4), "90")
    print("\n" + bar)
    print(c(f"  {text}  ", "1;96"))
    print(bar)

def info(text):
    print(c("• ", "94") + text)

def ok(text):
    print(c("✔ ", "92") + text)

def warn(text):
    print(c("! ", "93") + text)

def err(text):
    print(c("✖ ", "91") + text)

class Spinner:
    def __init__(self, label="Working"):
        self.label = label
        self._stop = threading.Event()
        self._thread = None
        self._start_ts = None

    def start(self):
        self._start_ts = time.perf_counter()
        def run():
            i = 0
            while not self._stop.is_set():
                frame = SPIN_FRAMES[i % len(SPIN_FRAMES)]
                elapsed = time.perf_counter() - self._start_ts
                msg = f"{self.label}  {frame}  {elapsed:5.1f}s"
                print("\r" + c(msg, "36"), end="", flush=True)
                time.sleep(0.08)
                i += 1
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        return self

    def stop(self, final=None):
        self._stop.set()
        if self._thread:
            self._thread.join()
        print("\r" + " " * 80, end="\r")
        if final:
            print(final)
        self._start_ts = None

def run_summarize_like():
    here = os.path.dirname(os.path.abspath(__file__))
    py = os.path.join(here, "summarize-project.py")
    bat = os.path.join(here, "summarize-project.bat")

    def _run(cmd, shell=False):
        try:
            proc = subprocess.Popen(cmd, shell=shell)
            proc.wait()
            return proc.returncode
        except FileNotFoundError:
            return 127
        except Exception:
            return 1

    if os.path.exists(py):
        return _run([sys.executable, py], shell=False)
    if os.path.exists(bat):
        return _run(bat, shell=True)
    warn("summarize-project not found; skipping snapshot step.")
    return 0

def read_programming_context():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "programming_context.txt")
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""

def prompt_user_changes():
    print(c("Please specifiy the changes", "93"))
    try:
        return input(c("> ", "96"))
    except EOFError:
        return ""

def build_system_instruction(programming_context_text):
    return (
        "<SYSTEM_PROMPT>\n"
        "<identity>\n"
        "You are an autonomous code-modding assistant. Do NOT wait for follow-ups. Read the request and immediately output the required Operation Directives to modify the project.\n"
        "</identity>\n\n"
        "<change_output_protocol>\n"
        "Return ONLY Operation Directives: <patch>, <file>, <delete>, <rename>, <binary>. No prose. Use unified diff for <patch>; use full-file content in <file>. Never output anything else.\n"
        "</change_output_protocol>\n\n"
        "<bracket_output_rule>\n"
        "In ALL code fences, <patch>, <file>, and inline code: output literal \"[\" and \"]\".\n"
        "</bracket_output_rule>\n\n"
        "<quality_gates>\n"
        "- Changes must be minimal, correct, and syntactically valid.\n"
        "- Do not ask for confirmation; make best-effort decisions.\n"
        "</quality_gates>\n"
        "</SYSTEM_PROMPT>\n\n"
        "<PROGRAMMING_CONTEXT>\n"
        f"{programming_context_text}\n"
        "</PROGRAMMING_CONTEXT>\n"
    )

def strip_fences(text):
    text = text.strip()
    fence = re.compile(r"^```(?:[a-zA-Z0-9_-]+)?\s*(.*?)\s*```$", re.DOTALL)
    m = fence.match(text)
    if m:
        return m.group(1).strip()
    return text

def call_gemini(user_request, system_instruction, model_id="gemini-2.5-pro"):
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        err("google-genai not installed.")
        info("Install with: " + c("pip install -U google-genai", "1"))
        sys.exit(1)

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        err("Missing GEMINI_API_KEY (or GOOGLE_API_KEY) in environment.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    cfg_kwargs = dict(
        system_instruction=system_instruction,
        temperature=0.0,
        top_p=1.0,
        top_k=64,
        candidate_count=1,
        max_output_tokens=8192,
        response_mime_type="text/plain",
    )

    thinking_cfg = None
    try:
        from google.genai import types as _t
        thinking_cfg = _t.ThinkingConfig(include_thoughts=True, thinking_budget=-1)
    except Exception:
        thinking_cfg = None

    if thinking_cfg is not None:
        cfg_kwargs["thinking_config"] = thinking_cfg

    try:
        config = types.GenerateContentConfig(**cfg_kwargs)
    except Exception:
        cfg_kwargs.pop("thinking_config", None)
        config = types.GenerateContentConfig(**cfg_kwargs)

    start = time.perf_counter()
    spinner = Spinner("Contacting Gemini (temperature 0.0)").start()
    try:
        resp = client.models.generate_content(
            model=model_id,
            contents=user_request,
            config=config,
        )
    finally:
        elapsed = time.perf_counter() - start
        spinner.stop(ok(f"Gemini responded in {elapsed:.1f}s"))
    try:
        return resp.text or ""
    except Exception:
        return str(resp)

def import_generate_project_module():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "generate-project.py")
    if not os.path.exists(path):
        err("generate-project.py not found; cannot apply changes.")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("generate_project", path)
    if spec is None or spec.loader is None:
        err("Failed to load generate-project module spec.")
        sys.exit(1)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    h1("Project snapshot")
    sp = Spinner("Running summarize-project").start()
    rc = 0
    try:
        rc = run_summarize_like()
    finally:
        sp.stop(ok("Snapshot step completed." if rc == 0 else "Snapshot step finished with warnings."))

    h1("Your requested changes")
    user_changes = prompt_user_changes().strip()
    if not user_changes:
        err("No change request provided. Exiting.")
        sys.exit(1)

    h1("Preparing system instruction")
    info("Loading programming_context.txt")
    programming_context_text = read_programming_context()
    system_instruction = build_system_instruction(programming_context_text)
    ok("Instruction prepared.")

    h1("Gemini code modification")
    info("Fetching GEMINI_API_KEY from environment")
    result_text = call_gemini(user_changes, system_instruction)
    clean_text = strip_fences(result_text).strip()

    if (DEBUG):
        print(result_text)
    
    if not clean_text:
        err("Gemini returned an empty response.")
        sys.exit(1)
    ok("Received Operation Directives from Gemini.")

    h1("Applying directives via generate-project")
    gen_mod = import_generate_project_module()
    start = time.perf_counter()
    spinner = Spinner("Parsing and applying operations").start()
    try:
        exit_code = gen_mod.run_from_directives_text(
            clean_text,
            debug=False,
            fuzzy_threshold=0.88,
            backup=False
        )
    finally:
        spinner.stop()
    elapsed = time.perf_counter() - start
    if exit_code == 0:
        ok(f"Project updated successfully in {elapsed:.1f}s.")
        h1("All done")
        ok("Workflow complete. Review the logs above.")
    else:
        err(f"Generator reported errors after {elapsed:.1f}s. See logs above.")
        sys.exit(exit_code)

if __name__ == "__main__":
    main()