"""src/core/platform/windows/single_instance.py

Windows 名前付きミューテックス (CreateMutexW) を使用した多重起動排他制御。
"""

from __future__ import annotations

import ctypes
import logging
import sys

from src.core.platform.errors import SingleInstanceError, UnsupportedFeatureError

logger = logging.getLogger(__name__)

_DEFAULT_MUTEX_NAME = "Local\\ClipWatcher_SingleInstance_Mutex"
_ERROR_ALREADY_EXISTS = 183


class WindowsSingleInstanceController:
    """Windows 名前付きミューテックスを用いた単一インスタンス排他制御。"""

    def __init__(self, mutex_name: str = _DEFAULT_MUTEX_NAME) -> None:
        self.mutex_name = mutex_name
        self._mutex_handle: int | None = None

    def acquire(self) -> bool:
        """排他ミューテックスを取得する。

        Returns:
            True: ロックを取得した。
            False: 他のインスタンスが起動中。

        Raises:
            SingleInstanceError: ロック取得 API の失敗（重複起動とは区別する）。
            UnsupportedFeatureError: Windows 以外で呼び出された。
        """
        if sys.platform != "win32":
            raise UnsupportedFeatureError("single_instance", sys.platform)

        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            create_mutex = kernel32.CreateMutexW
            create_mutex.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
            create_mutex.restype = ctypes.c_void_p

            handle = create_mutex(None, False, self.mutex_name)
            error_code = ctypes.get_last_error()
        except Exception as e:
            raise SingleInstanceError(
                f"ミューテックスの取得中に例外が発生しました: {e}"
            ) from e

        if not handle:
            raise SingleInstanceError(
                f"CreateMutexW の呼び出しに失敗しました (エラーコード: {error_code})"
            )

        if error_code == _ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(ctypes.c_void_p(handle))
            return False

        self._mutex_handle = int(handle)
        return True

    def release(self) -> None:
        """保持しているミューテックスのハンドルを閉じる。未取得なら何もしない。"""
        if sys.platform == "win32" and self._mutex_handle is not None:
            try:
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel32.CloseHandle(ctypes.c_void_p(self._mutex_handle))
            except Exception as e:
                logger.warning(
                    "ミューテックスハンドルの解放中に例外が発生しました: %s", e
                )
            finally:
                self._mutex_handle = None
