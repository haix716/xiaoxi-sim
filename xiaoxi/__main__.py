"""python -m xiaoxi [port] [--open]：启动示教台服务（uvicorn 单进程，无 reload）。

生产/双击入口；开发热重载用：
  uv run uvicorn xiaoxi.app:app --reload --reload-dir xiaoxi --port 8777
"""
import argparse
import sys
import threading
import webbrowser

import uvicorn

from xiaoxi.app import create_app
from xiaoxi.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="xiaoxi", description="小犀示教台服务")
    parser.add_argument("port", nargs="?", type=int, default=None, help="端口（默认 8777）")
    parser.add_argument("--open", action="store_true", help="启动后自动开浏览器")
    args = parser.parse_args()

    settings = Settings()
    if args.port:
        settings = settings.model_copy(update={"port": args.port})
    application = create_app(settings)
    url = f"http://{settings.host}:{settings.port}"
    print(f"小犀示教台: {url}  （Ctrl+C 停）")
    if args.open:
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    try:
        uvicorn.run(application, host=settings.host, port=settings.port, log_level="warning")
    except OSError as e:
        print(f"端口 {settings.port} 起不来：{e}\n（多半被占了，换一个试试：python -m xiaoxi 8778）",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
