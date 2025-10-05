# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import argparse
import sys # Used to check command line argument count


def main():
    parser = argparse.ArgumentParser(
        description="CollabTrans: A collaborative translation platform.",
        epilog="Example: collabtrans -i  (start GUI)\ncollabtrans -i -p 8081 (enable port 8081)" # epilog will be displayed at the end of help information
    )
    parser.add_argument(
        "-i", "--interactive",  # Add a long option for better user experience
        action="store_true",    # When -i or --interactive appears, args.interactive will be True
        help="Open graphical user interface (GUI)."
    )

    parser.add_argument(
        "-p", "--port",
        type=int,  # Specify parameter type (e.g., integer)
        default=None,  # Default value (optional)
        help="Specify port number (default: 8010)."
    )

    parser.add_argument(
         "--version",  # Add a long option for better user experience
        action="store_true",
        help="View version number."
    )
    # If you want to add other non-GUI command line features in the future, you can add more parameters here
    # parser.add_argument("input_file", help="File path to translate", nargs="?") # nargs="?" makes it optional
    # parser.add_argument("-l", "--language", help="Target language")

    # Check if no arguments are provided (except the script name itself)
    # sys.argv[0] is the script name, len(sys.argv) == 1 means only the command itself was run without additional arguments
    if len(sys.argv) == 1:
        # If user only entered 'collabtrans' without any arguments
        print("Welcome to CollabTrans!")
        print("Please use '-i' or '--interactive' option to start the graphical interface.")
        print("\nExamples:")
        print("  collabtrans -i")
        print("  collabtrans --interactive")
        print("\nTo view all available options, run:")
        sys.exit(0) # Normal exit

    args = parser.parse_args()

    # Call core logic
    if args.interactive: # Note: this is args.interactive, corresponding to "--interactive"
        from collabtrans.app import run_app
        run_app(port=args.port)
    elif args.version:
        from collabtrans import  __version__
        print(__version__)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()