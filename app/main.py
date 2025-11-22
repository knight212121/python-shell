import sys
import os
import subprocess


def tokenize_string(s, cmd="cat"):
    in_single_quotes = False
    in_double_quotes = False
    i = 0
    result = []
    buf = []
    while i < len(s):
        c = s[i]
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

        if c == "'" and not in_double_quotes:
            in_single_quotes = not in_single_quotes
            i += 1
            continue

        if c == '"' and not in_single_quotes:
            in_double_quotes = not in_double_quotes
            i += 1
            continue

        if not (in_single_quotes or in_double_quotes) and c.isspace():
            if buf:
                result.append("".join(buf))
                buf = []
            i += 1

            if cmd == "echo":
                buf.append(" ")

            while i < len(s) and s[i].isspace():
                i += 1
            continue

        buf.append(c)
        i += 1

    if buf:
        result.append("".join(buf))

    return result


def echo(string):
    tokens = tokenize_string(string, "echo")
    for i in tokens:
        print(i, end="")
    print()


def exit_shell(code):
    if not code:
        code = "0"
    sys.exit(int(code))


def find_executable(executable):
    path_dirs = os.environ["PATH"].split(os.pathsep)
    for path in path_dirs:
        if os.path.exists(path):
            for exec in os.listdir(path):
                file_path = os.path.join(path, exec)
                if os.access(file_path, os.X_OK) and exec == executable:
                    return file_path

    return ""


def type_of(command):
    if command in shell_builtins:
        print(f"{command} is a shell builtin")
        return

    file_path = find_executable(command)
    if file_path:
        print(f"{command} is {file_path}")
        return

    print(f"{command}: not found")


def pwd(_):
    print(os.getcwd())


def cd(directory):
    if directory[0] == "~":
        directory = directory.replace("~", os.getenv("HOME"))
    normalized = os.path.normpath(directory)
    cwd = os.getcwd()
    target_path = os.path.join(cwd, normalized)
    if os.path.exists(target_path):
        os.chdir(target_path)
    else:
        print(f"cd: {target_path}: No such file or directory")


def run_command(command):
    command = tokenize_string(command)
    executable = find_executable(command[0])
    redirect_output = False
    redirect_file = ""

    if ">" in command or "1>" in command:
        redirect_file = command[-1]
        redirect_output = True
        command = command[:-2]

    if executable:
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        process.wait()
        for line in process.stdout or []:
            if redirect_output:
                with open(redirect_file, "w", encoding="utf-8") as f:
                    f.write(line.decode("utf-8") + "\n")
            else:
                print(line.decode("utf-8"), end="")
        return

    print(f"{command[0]}: command not found")


def cat(command):
    executable = find_executable("cat")
    args = tokenize_string(command, "cat")
    command = ["cat"]
    command.extend(args)
    if executable:
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        process.wait()
        for line in process.stdout or []:
            print(line.decode("utf-8"), end="")
        return


commands = {
    "echo": echo,
    "exit": exit_shell,
    "type": type_of,
    "pwd": pwd,
    "cd": cd,
    "cat": cat,
}

shell_builtins = {"echo", "exit", "type", "pwd", "cd"}


def main():
    while True:
        sys.stdout.write("$ ")
        command = input()
        # if command[:4] == "echo":
        #     commands[command[:4]](command[5:])
        # elif command[:4] == "exit":
        #     commands[command[:4]](int(command[5]))
        # elif command[:4] == "type":
        #     commands[command[:4]](command[5:])
        # elif command[:3] == "pwd":
        #     commands[command[:3]]()
        # else:
        #     run_command(command)
        cmd, *args = command.split(maxsplit=1)
        handler = commands.get(cmd)

        if handler:
            handler(args[0] if args else "")
        else:
            run_command(command)


if __name__ == "__main__":
    main()
