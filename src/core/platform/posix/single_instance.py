"""src/core/platform/posix/single_instance.py

POSIX (macOS / Linux) 環境向けの fcntl.flock ロックファイルを用いた多重起動排他制御。
"""

from __future__ import annotations

import errno
import logging
import os
from pathlib import Path
from typing import TextIO

from src.core.platform.errors import SingleInstanceError

logger = logging.getLogger(__name__)

_DEFAULT_LOCK_DIR = Path.home() / ".clipwatcher"
_DEFAULT_LOCK_FILE = _DEFAULT_LOCK_DIR / "clip_watcher.lock"


class PosixSingleInstanceController:
    """fcntl.flock を用いた単一インスタンス排他制御。"""

    def __init__(self, lock_file_path: Path | str | None = None) -> None:
        self.lock_file_path = (
            Path(lock_file_path) if lock_file_path else _DEFAULT_LOCK_FILE
        )
        self._file: TextIO | None = None

    def acquire(self) -> bool:
        """排他ロックを取得する。

        Returns:
            True: ロックを取得できた（本プロセスが唯一のインスタンス）。
            False: すでに別のインスタンスが起動中。

        Raises:
            SingleInstanceError: 排他制御の初期化や OS API 呼び出し自体が失敗した。
        """
        try:
            import fcntl
        except ImportError as e:
            raise SingleInstanceError("fcntl モジュールが利用できません") from e

        try:
            self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
            f = open(self.lock_file_path, "a+", encoding="utf-8")
        except Exception as e:
            raise SingleInstanceError(
                f"ロックファイル {self.lock_file_path} のオープンに失敗しました: {e}"
            ) from e

        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            f.seek(0)
            f.truncate(0)
            f.write(f"{os.getpid()}\n")
            f.flush()
            self._file = f
            logger.debug(
                "排他ロックを取得しました: %s (PID: %d)",
                self.lock_file_path,
                os.getpid(),
            )
            return True
        except (BlockingIOError, OSError) as e:
            # 他のインスタンスがすでにロックを保持している場合
            if isinstance(e, BlockingIOError) or e.errno in (
                errno.EACCES,
                errno.EAGAIN,
                errno.EWOULDBLOCK,
            ):
                logger.info(
                    "別のインスタンスが起動中です（ロック取得不可: %s）",
                    self.lock_file_path,
                )
                try:
                    f.close()
                except Exception:
                    pass
                return False

            # ロック取得 API 自体の予期せぬ失敗
            try:
                f.close()
            except Exception:
                pass
            raise SingleInstanceError(f"ロックの取得に失敗しました: {e}") from e

    def release(self) -> None:
        """排他ロックを解放する。未取得の状態で呼んでも何もしない（冪等）。"""
        if self._file is not None:
            try:
                import fcntl

                try:
                    fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
                except Exception as e:
                    logger.debug("flock の解除中にエラー: %s", e)
                self._file.close()
                logger.debug("排他ロックを解放しました: %s", self.lock_file_path)
            except Exception as e:
                logger.debug("ロックファイルの解放中にエラー: %s", e)
            finally:
                self._file = None
