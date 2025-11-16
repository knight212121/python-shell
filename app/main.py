import sys


def main():
    sys.stdout.write("$ ")
    command = input()
    sys.stdout.write(command + ": command not found")
    pass


if __name__ == "__main__":
    main()
