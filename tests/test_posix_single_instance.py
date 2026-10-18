"""tests/test_posix_single_instance.py

PosixSingleInstanceController の単体テスト。
fcntl.flock を用いた多重起動排他制御の契約を検証する。
"""

from __future__ import annotations

import errno
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.platform.errors import SingleInstanceError
from src.core.platform.posix.single_instance import PosixSingleInstanceController
from src.core.platform.protocols import SingleInstanceController


class TestPosixSingleInstanceController:
    def test_implements_protocol(self, tmp_path: Path) -> None:
        controller = PosixSingleInstanceController(tmp_path / "test.lock")
        assert isinstance(controller, SingleInstanceController)

    @pytest.mark.skipif(
        sys.platform == "win32", reason="POSIX fcntl is not available on Windows"
    )
    def test_real_acquire_and_release(self, tmp_path: Path) -> None:
        lock_file = tmp_path / "test_app.lock"
        c1 = PosixSingleInstanceController(lock_file)
        c2 = PosixSingleInstanceController(lock_file)

        # 最初のインスタンスはロック取得に成功する
        assert c1.acquire() is True
        assert lock_file.exists()
        assert len(lock_file.read_text(encoding="utf-8").strip()) > 0

        # 2番目のインスタンスは重複起動として False を返す
        assert c2.acquire() is False

        # c1 を解放
        c1.release()

        # 解放後は c2 が取得できるようになる
        assert c2.acquire() is True
        c2.release()

    def test_release_idempotent(self, tmp_path: Path) -> None:
        controller = PosixSingleInstanceController(tmp_path / "test.lock")
        # 未取得の状態で release を呼んでも何もしない
        controller.release()
        controller.release()

    def test_acquire_raises_single_instance_error_on_open_failure(
        self, tmp_path: Path
    ) -> None:
        lock_file = tmp_path / "test.lock"
        controller = PosixSingleInstanceController(lock_file)

        with (
            patch("pathlib.Path.mkdir"),
            patch("builtins.open", side_effect=PermissionError("Permission denied")),
        ):
            with pytest.raises(SingleInstanceError) as exc_info:
                controller.acquire()
            assert "オープンに失敗" in str(exc_info.value)

    def test_acquire_handles_blocking_io_error_mocked(self, tmp_path: Path) -> None:
        lock_file = tmp_path / "test.lock"
        controller = PosixSingleInstanceController(lock_file)
        mock_file = MagicMock()

        mock_fcntl = MagicMock()
        mock_fcntl.flock.side_effect = BlockingIOError(
            "Resource temporarily unavailable"
        )

        with (
            patch("builtins.open", return_value=mock_file),
            patch.dict(sys.modules, {"fcntl": mock_fcntl}),
        ):
            assert controller.acquire() is False
            mock_file.close.assert_called_once()

    def test_acquire_handles_errno_eagain_mocked(self, tmp_path: Path) -> None:
        lock_file = tmp_path / "test.lock"
        controller = PosixSingleInstanceController(lock_file)
        mock_file = MagicMock()

        os_err = OSError("Resource temporarily unavailable")
        os_err.errno = errno.EAGAIN
        mock_fcntl = MagicMock()
        mock_fcntl.flock.side_effect = os_err

        with (
            patch("builtins.open", return_value=mock_file),
            patch.dict(sys.modules, {"fcntl": mock_fcntl}),
        ):
            assert controller.acquire() is False
            mock_file.close.assert_called_once()

    def test_acquire_raises_single_instance_error_on_unexpected_flock_error(
        self, tmp_path: Path
    ) -> None:
        lock_file = tmp_path / "test.lock"
        controller = PosixSingleInstanceController(lock_file)
        mock_file = MagicMock()

        os_err = OSError("Unexpected device error")
        os_err.errno = errno.EIO
        mock_fcntl = MagicMock()
        mock_fcntl.flock.side_effect = os_err

        with (
            patch("builtins.open", return_value=mock_file),
            patch.dict(sys.modules, {"fcntl": mock_fcntl}),
        ):
            with pytest.raises(SingleInstanceError) as exc_info:
                controller.acquire()
            assert "ロックの取得に失敗" in str(exc_info.value)
            mock_file.close.assert_called_once()
