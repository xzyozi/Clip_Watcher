"""src/core/platform/macos/clipboard_reader.py

macOS 用の pbpaste コマンドを使用したクリップボード読み取り実装。

macOS 標準の `/usr/bin/pbpaste` を使用するため、外部ライブラリへの依存は不要（ゼロインストール）。
tkinter の ``clipboard_get()`` が失敗した場合の代替経路として使用する。
"""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


class MacOSClipboardReader:
    """pbpaste コマンドを用いたクリップボードのテキスト読み取り。"""

    def __init__(self, command: str = "pbpaste") -> None:
        self._command = command

    def read_text(self) -> str | None:
        """クリップボードのテキストを返す。

        取得に失敗した場合は None、テキスト形式が処理できない場合（空や非テキスト）は空文字を返す。
        """
        try:
            result = subprocess.run(
                [self._command],
                capture_output=True,
                timeout=1.0,
                check=False,
            )
            if result.returncode != 0:
                logger.warning(
                    "pbpaste がエラー終了しました (exit code: %d, stderr: %s)",
                    result.returncode,
                    result.stderr.decode("utf-8", errors="replace"),
                )
                return None
            return result.stdout.decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            logger.warning("pbpaste コマンドがタイムアウトしました。")
            return None
        except FileNotFoundError:
            logger.error("pbpaste コマンドが見つかりません。")
            return None
        except Exception as e:
            logger.error(
                "pbpaste によるクリップボード読み取りに失敗しました: %s",
                e,
                exc_info=True,
            )
            return None
