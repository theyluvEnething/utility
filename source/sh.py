#!/usr/bin/env python3
import cmd
import os
import re
import subprocess
import sys

class ShInterpreter(cmd.Cmd):
    intro = 'Welcome to the sh-lite interpreter. Type help or ? to list commands.'
    prompt = '$ '

    def __init__(self):
        super().__init__()
        self.env = os.environ.copy()

    def preloop(self):
        self._update_prompt()

    def postcmd(self, stop, line):
        self._update_prompt()
        return stop

    def _update_prompt(self):
        try:
            cwd = os.getcwd()
        except FileNotFoundError:
            cwd = "[invalid path]"
        self.prompt = f'{cwd}$ '

    def _expand_vars(self, s):
        def repl(match):
            var_name = match.group(1)
            return self.env.get(var_name, '')

        s = re.sub(r'\$(\w+)', repl, s)
        s = re.sub(r'\$\{(\w+)\}', repl, s)
        return s

    def do_cd(self, arg):
        """Change the current working directory. Usage: cd [path]"""
        path = self._expand_vars(arg).strip()
        if not path:
            path = self.env.get('HOME', os.path.expanduser('~'))

        try:
            os.chdir(path)
        except Exception as e:
            print(f"cd: {e}", file=sys.stderr)

    def do_export(self, arg):
        """Set an environment variable for this session. Usage: export KEY=value"""
        arg = self._expand_vars(arg).strip()
        match = re.match(r'(\w+)=(.*)', arg)
        if match:
            key, value = match.groups()
            self.env[key] = value.strip().strip('"\'')
        else:
            print("Usage: export KEY=value", file=sys.stderr)

    def default(self, line):
        """Execute a command in the system shell."""
        line = self._expand_vars(line)
        if not line:
            return

        try:
            subprocess.run(line, shell=True, env=self.env)
        except Exception as e:
            print(f"Error executing command: {e}", file=sys.stderr)

    def do_exit(self, arg):
        """Exit the interpreter."""
        return True

    def do_EOF(self, arg):
        """Exit the interpreter with Ctrl+D."""
        print()
        return True

    def emptyline(self):
        """Do nothing on an empty line."""
        pass

def run_script(interpreter, script_path, args):
    if not os.path.exists(script_path):
        print(f"sh: {script_path}: No such file or directory", file=sys.stderr)
        sys.exit(127)

    for i, arg in enumerate(args):
        interpreter.env[str(i + 1)] = arg
    interpreter.env['@'] = ' '.join(args)
    interpreter.env['#'] = str(len(args))

    try:
        with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                stripped_line = line.strip()
                if not stripped_line or stripped_line.startswith('#'):
                    continue
                if interpreter.onecmd(stripped_line):
                    break
    except Exception as e:
        print(f"Error reading or executing script {script_path}: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    interpreter = ShInterpreter()

    if len(sys.argv) > 1:
        script_path = sys.argv
        script_args = sys.argv[2:]
        
        script_dir = os.path.dirname(script_path)
        if script_dir:
            os.chdir(script_dir)
        
        run_script(interpreter, os.path.basename(script_path), script_args)
    else:
        interpreter.cmdloop()

if __name__ == "__main__":
    main()