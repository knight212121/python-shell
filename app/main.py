import sys


def main():
    while True:
        sys.stdout.write("$ ")
        command = input()
        if command[:4] == "echo":
            print(command[5:])
        elif command[:4] == "exit":
            return int(command[5])
        else:
            print(f"{command}: command not found")
    pass


if __name__ == "__main__":
    main()
