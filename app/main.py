import sys
import os
import subprocess

def echo(string):
    print(string)

def exit_shell(code):
    sys.exit(code)

def type_of(command):
    if command in commands:
        print(f"{command} is a shell builtin")
        return

    path_dirs = os.environ["PATH"].split(os.pathsep)
    # os.access("/usr/local/bin/catnap", os.X_OK)
    for path in path_dirs:
        if os.path.exists(path):
            for executable in os.listdir(path):
                file_path = os.path.join(path, executable)
                if os.access(file_path, os.X_OK) and executable == command:
                    print(f"{command} is {file_path}")
                    return

    print(f"{command}: not found")

commands = {
    "echo": echo,
    "exit": exit_shell,
    "type": type_of,
}

def run_command(command):
    command = command.split()
    path_dirs = os.environ["PATH"].split(os.pathsep)
    for path in path_dirs:
        if os.path.exists(path):
            for executable in os.listdir(path):
                file_path = os.path.join(path, executable)
                if os.access(file_path, os.X_OK) and executable == command[0]:
                    process = subprocess.Popen(command, stdout=subprocess.PIPE)
                    process.wait()
                    for line in process.stdout:
                        print(line.decode("utf-8"), end="")
                    return

    print(f"{command}: not found")

def main():
    while True:
        sys.stdout.write("$ ")
        command = input()
        if command[:4] == "echo":
            commands[command[:4]](command[5:])
        elif command[:4] == "exit":
            commands[command[:4]](int(command[5]))
        elif command[:4] == "type":
            commands[command[:4]](command[5:])
        else:
            run_command(command)

    pass


if __name__ == "__main__":
    main()
