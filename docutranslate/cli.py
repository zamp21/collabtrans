import argparse
import sys # 用于检查命令行参数数量


def main():
    parser = argparse.ArgumentParser(
        description="DocuTranslate: 一个文档翻译工具。",
        epilog="示例: docutranslate -i  (启动图形界面)\ndocutranslate -i -p 8081 (启用端口号8081)" # epilog 会显示在帮助信息的末尾
    )
    parser.add_argument(
        "-i", "--interactive",  # 添加一个长选项，更友好
        action="store_true",    # 当出现 -i 或 --interactive 时，args.interactive 将为 True
        help="打开图形化用户界面 (GUI)。"
    )

    parser.add_argument(
        "-p", "--port",
        type=int,  # 指定参数类型（例如整数）
        default=None,  # 默认值（可选）
        help="指定端口号（默认：8010）。"
    )

    parser.add_argument(
         "--version",  # 添加一个长选项，更友好
        action="store_true",
        help="查看版本号。"
    )
    # 如果你想在未来添加其他非GUI的命令行功能，可以在这里添加更多参数
    # parser.add_argument("input_file", help="要翻译的文件路径", nargs="?") # nargs="?" 使其可选
    # parser.add_argument("-l", "--language", help="目标语言")

    # 检查是否没有提供任何参数 (除了脚本名本身)
    # sys.argv[0] 是脚本名, len(sys.argv) == 1 表示只运行了命令本身，没有附加参数
    if len(sys.argv) == 1:
        # 如果用户只输入了 'docutranslate' 而没有任何参数
        print("欢迎使用 DocuTranslate！")
        print("请使用 '-i' 或 '--interactive' 选项来启动图形化界面。")
        print("\n示例:")
        print("  docutranslate -i")
        print("  docutranslate --interactive")
        print("\n如需查看所有可用选项，请运行:")
        sys.exit(0) # 正常退出

    args = parser.parse_args()

    # 调用核心逻辑
    if args.interactive: # 注意这里是 args.interactive，对应 "--interactive"
        from docutranslate.app import run_app
        run_app(port=args.port)
    elif args.version:
        from docutranslate import  __version__
        print(__version__)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()