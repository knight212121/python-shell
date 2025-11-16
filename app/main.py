import sys
import os

def echo(string):
    print(string)

def exit_shell(code):
    sys.exit(code)

def type_of(command):
    if command in commands:
        print(f"{command[5:]} is a shell builtin")
        return

    path_dirs = os.environ["PATH"].split(os.pathsep)
    # os.access("/usr/local/bin/catnap", os.X_OK)
    for path in path_dirs:
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
            print(f"{command}: command not found")
    pass


if __name__ == "__main__":
    main()
