import sys
import tty
import termios
import os
import subprocess


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

    def pwd(self, _):
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
        self.last_prefix = None
        self.matches = []
        self.index = 0
        self.executables = list(self.builtins.commands.keys())
        if "PATH" not in os.environ:
            return ""

        path_dirs = os.environ["PATH"].split(os.pathsep)
        for path in path_dirs:
            if os.path.exists(path):
                try:
                    for entry in os.listdir(path):
                        file_path = os.path.join(path, entry)
                        if os.access(file_path, os.X_OK):
                            exec = file_path.split("/")
                            self.executables.append(exec[-1])
                except OSError:
                    continue



    def autocomplete(self, buffer):
        parts = buffer.split()
        if not parts:
            prefix = ""
        else:
            prefix = parts[-1]

        if prefix != self.last_prefix:
            self.last_prefix = prefix
            self.matches = [
                cmd for cmd in self.executables if cmd.startswith(prefix)
            ]
            self.index = 0

        if not self.matches:
            return buffer + "\x07"

        match = self.matches[self.index]
        self.index = (self.index + 1) % len(self.matches)

        new_buffer = " ".join(parts[:-1] + [match])
        return new_buffer + " "


class Shell:
    """Main shell class that coordinates all components"""

    def __init__(self):
        self.tokenizer = Tokenizer()
        self.path_resolver = PathResolver()
        self.builtins = BuiltinCommands(self)
        self.executor = CommandExecutor(self.builtins, self.path_resolver)
        self.completer = AutoCompleter(self.builtins)

    def enter_raw_mode(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
        tty.setraw(self.fd)

    def exit_raw_mode(self):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)

    def redraw_prompt(self, buffer):
        sys.stdout.write("\r")
        sys.stdout.write("\x1b[k")
        sys.stdout.write("\r$ " + buffer)
        sys.stdout.flush()

    def read_line(self):
        buffer = ""
        self.enter_raw_mode()

        try:
            while True:
                sys.stdout.write("\r$ " + buffer)
                sys.stdout.write("\x1b[K")
                sys.stdout.flush()
                ch = sys.stdin.read(1)

                if ch == "\n" or ch == "\r":
                    sys.stdout.write("\r\n")
                    break

                elif ch == "\t":
                    buffer = self.completer.autocomplete(buffer)

                elif ch == "\x7f":  # Backspace
                    if len(buffer) > 0:
                        buffer = buffer[:-1]

                elif ch == "\x03":  # Ctrl C
                    sys.stdout.write("^C\r\n")
                    raise KeyboardInterrupt

                elif ch == "\x04":  # Ctrl D
                    if buffer == "":
                        sys.stdout.write("\r\n")
                        raise EOFError

                else:
                    buffer += ch
                    self.redraw_prompt(buffer)
        finally:
            self.exit_raw_mode()

        return buffer

    def run(self):
        """Main shell execution loop"""

        while True:
            try:
                command_input = self.read_line()

                if not command_input:
                    continue

                # Tokenize and execute command
                tokens = self.tokenizer.tokenize_string(command_input)
                self.executor.run_command(tokens)

            except EOFError:
                print("Use exit")
                continue
            except KeyboardInterrupt:
                print("Ctrl C")
                continue


def main():
    """Entry point for the shell"""
    shell = Shell()
    shell.run()


if __name__ == "__main__":
    main()
