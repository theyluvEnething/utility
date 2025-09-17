#!/usr/bin/env python3
import os
import sys
import subprocess

def run_summarize_like():
    here = os.path.dirname(os.path.abspath(__file__))
    py = os.path.join(here, 'summarize-project.py')
    bat = os.path.join(here, 'summarize-project.bat')
    try:
        if os.path.exists(py):
            subprocess.run([sys.executable, py], check=False)
            return
        if os.path.exists(bat):
            subprocess.run(bat, shell=True, check=False)
            return
        print("Warning: summarize-project not found; skipping copy step.", file=sys.stderr)
    except Exception as e:
        print(f"Warning: failed running summarize-project: {e}", file=sys.stderr)

def read_programming_context():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, 'programming_context.txt')
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        return ""

def color(text, code="96"):
    return f"\033[{code}m{text}\033[0m"

def prompt_user_changes():
    print(color("Please specifiy the changes", "93"))
    try:
        return input(color("> ", "96"))
    except EOFError:
        return ""

def build_system_instruction(programming_context_text):
    sys_prompt = (
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
    return sys_prompt

def call_gemini(user_request, system_instruction, model_id="gemini-2.5-pro"):
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("Error: google-genai not installed. Install with: pip install -U google-genai", file=sys.stderr)
        sys.exit(1)

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: Set GEMINI_API_KEY (or GOOGLE_API_KEY) in your environment.", file=sys.stderr)
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
    except Exception as e:
        print(f"Warning: GenerateContentConfig issue ({e}); retrying without thinking_config.")
        cfg_kwargs.pop("thinking_config", None)
        config = types.GenerateContentConfig(**cfg_kwargs)

    resp = client.models.generate_content(
        model=model_id,
        contents=user_request,
        config=config,
    )
    try:
        return resp.text or ""
    except Exception:
        return str(resp)

def main():
    run_summarize_like()
    user_changes = prompt_user_changes().strip()
    if not user_changes:
        print("No input provided; exiting.", file=sys.stderr)
        sys.exit(1)
    programming_context_text = read_programming_context()
    system_instruction = build_system_instruction(programming_context_text)
    result = call_gemini(user_changes, system_instruction)
    print("\n=== GEMINI RESPONSE ===\n")
    print(result)

if __name__ == "__main__":
    main()