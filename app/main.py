import sys
import os
import subprocess
import readline
from pynput.keyboard import Key
from pynput import keyboard


class Tokenizer:
    """Handles string tokenization with quote and escape character support"""

    @staticmethod
    def tokenize_string(s):
        in_single_quotes = False
        in_double_quotes = False
        i = 0
        result = []
        buf = []

        while i < len(s):
            c = s[i]

            # Handle escape characters
            if c == "\\":
                if in_double_quotes:
                    if i + 1 < len(s):
                        next_char = s[i + 1]
                        if next_char in ['"', "$", "\\", "`"]:
                            buf.append(next_char)
                            i += 2
                            continue
                        else:
                            buf.append(c)
                            i += 1
                            continue
                elif in_single_quotes:
                    buf.append(c)
                    i += 1
                    continue

                if i + 1 < len(s):
                    buf.append(s[i + 1])
                    i += 2
                    continue

            # Handle quotes
            if c == "'" and not in_double_quotes:
                in_single_quotes = not in_single_quotes
                i += 1
                continue

            if c == '"' and not in_single_quotes:
                in_double_quotes = not in_double_quotes
                i += 1
                continue

            # Handle whitespace (only outside quotes)
            if not (in_single_quotes or in_double_quotes) and c.isspace():
                if buf:
                    result.append("".join(buf))
                    buf = []
                i += 1

                # Skip additional whitespace
                while i < len(s) and s[i].isspace():
                    i += 1
                continue

            buf.append(c)
            i += 1

        if buf:
            result.append("".join(buf))

        return result


class BuiltinCommands:
    """Handles all built-in shell commands"""

    def __init__(self, shell):
        self.shell = shell
        self.commands = {
            "echo": self.echo,
            "exit": self.exit_shell,
            "type": self.type_of,
            "pwd": self.pwd,
            "cd": self.cd,
        }

    def echo(self, args):
        """Print arguments to stdout"""
        print(" ".join(args))

    def exit_shell(self, args):
        """Exit the shell"""
        code = args[0] if args else "0"
        sys.exit(int(code))

    def type_of(self, args):
        """Determine if a command is a builtin or external executable"""
        if not args:
            return

        command = args[0]
        if command in self.commands:
            print(f"{command} is a shell builtin")
            return

        file_path = self.shell.path_resolver.find_executable(command)
        if file_path:
            print(f"{command} is {file_path}")
            return

        print(f"{command}: not found")

    def pwd(self, args):
        """Print current working directory"""
        print(os.getcwd())

    def cd(self, args):
        """Change directory"""
        if not args:
            return

        directory = args[0]
        if directory.startswith("~"):
            directory = directory.replace("~", os.getenv("HOME"))

        normalized = os.path.normpath(directory)
        cwd = os.getcwd()
        target_path = os.path.join(cwd, normalized)

        if os.path.exists(target_path):
            os.chdir(target_path)
        else:
            print(f"cd: {target_path}: No such file or directory")

    def is_builtin(self, command):
        """Check if command is a builtin"""
        return command in self.commands

    def execute(self, command, args):
        """Execute a builtin command"""
        if command in self.commands:
            self.commands[command](args)
            return True
        return False


class PathResolver:
    """Handles PATH resolution for external commands"""

    @staticmethod
    def find_executable(executable):
        """Find an executable in PATH"""
        if "PATH" not in os.environ:
            return ""

        path_dirs = os.environ["PATH"].split(os.pathsep)
        for path in path_dirs:
            if os.path.exists(path):
                try:
                    for entry in os.listdir(path):
                        file_path = os.path.join(path, entry)
                        if os.access(file_path, os.X_OK) and entry == executable:
                            return file_path
                except OSError:
                    continue
        return ""


class CommandExecutor:
    """Handles execution of both builtin and external commands"""

    def __init__(self, builtins, path_resolver):
        self.builtins = builtins
        self.path_resolver = path_resolver

    def run_command(self, command_tokens):
        """Execute a command with redirection support"""
        if not command_tokens:
            return

        command = command_tokens[0]
        args = command_tokens[1:] if len(command_tokens) > 1 else []

        # Handle output redirection
        redirect_info = self._parse_redirection(command_tokens)
        if redirect_info:
            command_tokens, redirect_file, redirect_type, append_mode = redirect_info
            command = command_tokens[0]
            args = command_tokens[1:] if len(command_tokens) > 1 else []

            return self._execute_with_redirection(
                command, args, redirect_file, redirect_type, append_mode
            )

        # Execute builtin or external command
        if self.builtins.is_builtin(command):
            self.builtins.execute(command, args)
        else:
            self._execute_external(command_tokens)

    def _parse_redirection(self, tokens):
        """Parse redirection operators from command tokens"""
        redirect_ops = [">", "1>", "2>", ">>", "1>>", "2>>"]

        for i, token in enumerate(tokens):
            if token in redirect_ops and i + 1 < len(tokens):
                redirect_file = tokens[i + 1]
                redirect_type = "stderr" if token in ["2>", "2>>"] else "stdout"
                append_mode = token.endswith(">>")
                command_tokens = tokens[:i]

                return command_tokens, redirect_file, redirect_type, append_mode
        return None

    def _execute_with_redirection(
        self, command, args, redirect_file, redirect_type, append_mode
    ):
        """Execute command with output redirection"""
        if self.builtins.is_builtin(command):
            # For builtins, we need to capture their output
            import io
            from contextlib import redirect_stdout, redirect_stderr

            mode = "a" if append_mode else "w"

            try:
                with open(redirect_file, mode, encoding="utf-8") as f:
                    if redirect_type == "stdout":
                        with redirect_stdout(f):
                            self.builtins.execute(command, args)
                    else:  # stderr
                        with redirect_stderr(f):
                            self.builtins.execute(command, args)
            except IOError as e:
                print(f"Error redirecting output: {e}")
        else:
            self._execute_external_with_redirection(
                [command] + args, redirect_file, redirect_type, append_mode
            )

    def _execute_external(self, command_tokens):
        """Execute an external command"""
        executable = self.path_resolver.find_executable(command_tokens[0])

        if executable:
            try:
                process = subprocess.run(
                    command_tokens,
                    capture_output=True,
                    text=True,
                )

                if process.stdout:
                    print(process.stdout, end="")
                if process.stderr:
                    print(process.stderr, end="")
            except Exception as e:
                print(f"Error executing command: {e}")
        else:
            print(f"{command_tokens[0]}: command not found")

    def _execute_external_with_redirection(
        self, command_tokens, redirect_file, redirect_type, append_mode
    ):
        """Execute external command with redirection"""
        executable = self.path_resolver.find_executable(command_tokens[0])

        if not executable:
            print(f"{command_tokens[0]}: command not found")
            return

        mode = "a" if append_mode else "w"

        try:
            process = subprocess.run(
                command_tokens,
                capture_output=True,
                text=True,
            )

            with open(redirect_file, mode, encoding="utf-8") as f:
                output = process.stderr if redirect_type == "stderr" else process.stdout
                if output:
                    f.write(output)

            # Print the other stream to terminal
            if process.stdout and redirect_type == "stderr":
                print(process.stdout, end="")
            if process.stderr and redirect_type == "stdout":
                print(process.stderr, end="")

        except IOError as e:
            print(f"Error with redirection: {e}")
        except Exception as e:
            print(f"Error executing command: {e}")


class AutoCompleter:
    """Handles tab completion for shell commands"""

    def __init__(self, builtins):
        self.builtins = builtins
        self.setup_readline()

    def setup_readline(self):
        """Initialize readline with tab completion"""
        readline.set_completer(self.autocomplete)
        readline.parse_and_bind("tab: complete")

    def autocomplete(self, text, state):
        """Auto-completion function for readline"""
        matches = [cmd for cmd in self.builtins.commands.keys() if cmd.startswith(text)]
        try:
            if state < len(matches):
                return matches[state]
        except IndexError:
            return None
        return None


class KeyboardHandler:
    """Handles keyboard input and special keys"""

    def __init__(self, completer):
        self.completer = completer

    def key_press(self, key):
        """Handle key press events"""
        if key == Key.tab:
            # Tab completion is handled by readline
            pass

    def start_listener(self):
        """Start the keyboard listener"""
        listener = keyboard.Listener(on_press=self.key_press)
        listener.start()
        return listener


class Shell:
    """Main shell class that coordinates all components"""

    def __init__(self):
        self.tokenizer = Tokenizer()
        self.path_resolver = PathResolver()
        self.builtins = BuiltinCommands(self)
        self.executor = CommandExecutor(self.builtins, self.path_resolver)
        self.completer = AutoCompleter(self.builtins)
        self.keyboard_handler = KeyboardHandler(self.completer)

    def run(self):
        """Main shell execution loop"""

        # Start keyboard listener
        listener = self.keyboard_handler.start_listener()

        try:
            while True:
                try:
                    sys.stdout.write("$ ")
                    command_input = input().strip()

                    if not command_input:
                        continue

                    # Tokenize and execute command
                    tokens = self.tokenizer.tokenize_string(command_input)
                    self.executor.run_command(tokens)

                except EOFError:
                    print("\nUse 'exit' to quit the shell")
                except KeyboardInterrupt:
                    print("\nUse 'exit' to quit the shell")

        finally:
            # Stop the keyboard listener
            listener.stop()


def main():
    """Entry point for the shell"""
    shell = Shell()
    shell.run()


if __name__ == "__main__":
    main()
