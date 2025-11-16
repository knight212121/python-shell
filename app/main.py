import sys



def echo(string):
    print(string)

def exit_shell(code):
    sys.exit(code)

def type_of(command):
    if command in commands:
        return True
    return False

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
            if commands[command[:4]](command[5:]):
                print(f"{command[5:]} is a shell builtin")
            else:
                print(f"{command[5:]}: not found")
        else:
            print(f"{command}: command not found")
    pass


if __name__ == "__main__":
    main()
