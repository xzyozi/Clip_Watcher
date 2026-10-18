"""src/core/platform/macos/hotkey.py

macOS (Carbon API / HIToolbox) を使用したグローバルホットキー監視の実装。

アクセシビリティ権限 (Accessibility / AX) を要求することなく、
RegisterEventHotKey / InstallEventHandler を ctypes 経由で呼び出して
バックグラウンド常駐中にもグローバルホットキーを検知する。
"""

from __future__ import annotations

import ctypes
import logging
import sys
import threading
import tkinter as tk
from collections.abc import Callable, Iterable
from typing import Any

from src.core.hotkey.global_hotkey_listener import GLOBAL_HOTKEY_ID, HotkeyRegistration

logger = logging.getLogger(__name__)

# macOS Carbon HotKey 修飾キー定数
CMD_KEY = 0x0100
SHIFT_KEY = 0x0200
OPTION_KEY = 0x0800
CONTROL_KEY = 0x1000

# Carbon Event 定数
K_EVENT_CLASS_KEYBOARD = 0x6B657962  # 'keyb'
K_EVENT_HOT_KEY_PRESSED = 5
K_EVENT_PARAM_DIRECT_OBJECT = 0x2D2D2D2D  # '----'
TYPE_EVENT_HOT_KEY_ID = 0x686B6964  # 'hkid'
EVENT_LOOP_TIMED_OUT_ERR = -9875

# 識別シグネチャ: 'CWHT' (ClipWatcher HotKey)
CWHT_SIGNATURE = 0x43574854

# CTypes 基本型定義
OSType = ctypes.c_uint32
OSStatus = ctypes.c_int32
ItemCount = ctypes.c_ulong
OptionBits = ctypes.c_uint32
ByteCount = ctypes.c_ulong
EventTimeout = ctypes.c_double
Boolean = ctypes.c_ubyte


class EventHotKeyID(ctypes.Structure):
    _fields_ = [
        ("signature", OSType),
        ("id", ctypes.c_uint32),
    ]


class EventTypeSpec(ctypes.Structure):
    _fields_ = [
        ("eventClass", OSType),
        ("eventKind", ctypes.c_uint32),
    ]


EventHandlerProc = ctypes.CFUNCTYPE(
    OSStatus,
    ctypes.c_void_p,  # inHandlerCallRef
    ctypes.c_void_p,  # inEvent
    ctypes.c_void_p,  # inUserData
)


def _load_carbon() -> Any | None:
    """Carbon フレームワークを安全に読み込み、関数プロトタイプを設定する。"""
    if sys.platform != "darwin":
        return None
    try:
        carbon = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/Carbon.framework/Carbon"
        )
    except OSError as e:
        logger.warning("Carbon フレームワークのロードに失敗しました: %s", e)
        return None

    carbon.GetEventDispatcherTarget.restype = ctypes.c_void_p
    carbon.GetEventDispatcherTarget.argtypes = []

    carbon.GetApplicationEventTarget.restype = ctypes.c_void_p
    carbon.GetApplicationEventTarget.argtypes = []

    carbon.InstallEventHandler.restype = OSStatus
    carbon.InstallEventHandler.argtypes = [
        ctypes.c_void_p,  # inTarget
        EventHandlerProc,  # inHandler
        ItemCount,  # inNumTypes
        ctypes.POINTER(EventTypeSpec),  # inList
        ctypes.c_void_p,  # inUserData
        ctypes.POINTER(ctypes.c_void_p),  # outRef
    ]

    carbon.RemoveEventHandler.restype = OSStatus
    carbon.RemoveEventHandler.argtypes = [ctypes.c_void_p]

    carbon.RegisterEventHotKey.restype = OSStatus
    carbon.RegisterEventHotKey.argtypes = [
        ctypes.c_uint32,  # inHotKeyCode
        ctypes.c_uint32,  # inHotKeyModifiers
        EventHotKeyID,  # inHotKeyID (値渡し)
        ctypes.c_void_p,  # inTarget
        OptionBits,  # inOptions
        ctypes.POINTER(ctypes.c_void_p),  # outRef
    ]

    carbon.UnregisterEventHotKey.restype = OSStatus
    carbon.UnregisterEventHotKey.argtypes = [ctypes.c_void_p]

    carbon.GetEventParameter.restype = OSStatus
    carbon.GetEventParameter.argtypes = [
        ctypes.c_void_p,  # inEvent
        OSType,  # inName
        OSType,  # inDesiredType
        ctypes.POINTER(OSType),  # outActualType
        ByteCount,  # inBufferSize
        ctypes.POINTER(ByteCount),  # outActualSize
        ctypes.c_void_p,  # outData
    ]

    carbon.ReceiveNextEvent.restype = OSStatus
    carbon.ReceiveNextEvent.argtypes = [
        ItemCount,  # inNumTypes
        ctypes.POINTER(EventTypeSpec),  # inList
        EventTimeout,  # inTimeout
        Boolean,  # inPullEvent
        ctypes.POINTER(ctypes.c_void_p),  # outEvent
    ]

    carbon.SendEventToEventTarget.restype = OSStatus
    carbon.SendEventToEventTarget.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    carbon.ReleaseEvent.restype = None
    carbon.ReleaseEvent.argtypes = [ctypes.c_void_p]

    return carbon


class MacOSHotkeyListener:
    """macOS 用グローバルホットキー監視リスナー。

    HotkeyListener Protocol に準拠し、バックグラウンドスレッドで Carbon イベントループ
    (ReceiveNextEvent) を回してホットキー押下を検知する。
    """

    def __init__(
        self,
        tk_root: tk.Tk,
        on_triggered: Callable[[int], None],
        *,
        carbon_lib: Any | None = None,
    ) -> None:
        self.tk_root = tk_root
        self.on_triggered = on_triggered
        self._carbon_lib = carbon_lib
        self._thread: threading.Thread | None = None
        self._running = False
        self._registered_keys: dict[int, ctypes.c_void_p] = {}
        self._handler_ref = ctypes.c_void_p()
        self._c_handler: Any = None
        self._lock = threading.Lock()

    def _get_carbon(self) -> Any | None:
        if self._carbon_lib is not None:
            return self._carbon_lib
        return _load_carbon()

    def _handle_carbon_event(
        self,
        _next_handler: ctypes.c_void_p,
        event: ctypes.c_void_p,
        _user_data: ctypes.c_void_p,
    ) -> int:
        carbon = self._get_carbon()
        if carbon is None:
            return 0

        hotkey_id = EventHotKeyID()
        status = carbon.GetEventParameter(
            event,
            K_EVENT_PARAM_DIRECT_OBJECT,
            TYPE_EVENT_HOT_KEY_ID,
            None,
            ctypes.sizeof(EventHotKeyID),
            None,
            ctypes.byref(hotkey_id),
        )
        if status == 0:
            target_id = int(hotkey_id.id)
            try:
                self.tk_root.after(0, self.on_triggered, target_id)
            except Exception as e:
                logger.error("ホットキー通知のディスパッチに失敗しました: %s", e)
        return 0

    def start(self, modifiers: int, vk_code: int) -> bool:
        """単一のグローバルホットキーを登録して監視を開始する。"""
        return self.start_many(
            [HotkeyRegistration(GLOBAL_HOTKEY_ID, modifiers, vk_code)]
        )

    def start_many(self, registrations: Iterable[Any]) -> bool:
        """複数のグローバルホットキー登録集合を受け取り、監視を開始する。"""
        entries = list(registrations)
        if len({entry.hotkey_id for entry in entries}) != len(entries):
            logger.error("重複したホットキーIDが指定されました。")
            return False

        if not entries:
            self.stop()
            return True

        if sys.platform != "darwin" and self._carbon_lib is None:
            logger.warning(
                "macOS 以外の環境のため、グローバルホットキー登録をスキップします。"
            )
            return False

        with self._lock:
            self.stop()
            carbon = self._get_carbon()
            if carbon is None:
                logger.warning("Carbon ライブラリの取得に失敗しました。")
                return False

            ready_event = threading.Event()
            result_holder: dict[str, bool] = {}

            def _run() -> None:
                target = carbon.GetEventDispatcherTarget()
                self._c_handler = EventHandlerProc(self._handle_carbon_event)
                event_type = EventTypeSpec(
                    K_EVENT_CLASS_KEYBOARD, K_EVENT_HOT_KEY_PRESSED
                )

                status = carbon.InstallEventHandler(
                    target,
                    self._c_handler,
                    1,
                    ctypes.byref(event_type),
                    None,
                    ctypes.byref(self._handler_ref),
                )
                if status != 0:
                    logger.warning(
                        "InstallEventHandler に失敗しました (status=%d)", status
                    )
                    result_holder["ok"] = False
                    ready_event.set()
                    return

                handler_installed = True
                registered: dict[int, ctypes.c_void_p] = {}
                for entry in entries:
                    ref = ctypes.c_void_p()
                    hk_id = EventHotKeyID(CWHT_SIGNATURE, entry.hotkey_id)
                    reg_status = carbon.RegisterEventHotKey(
                        entry.vk_code,
                        entry.modifiers,
                        hk_id,
                        target,
                        0,
                        ctypes.byref(ref),
                    )
                    if reg_status != 0:
                        logger.warning(
                            "グローバルホットキーの登録に失敗しました (ID: %s, status=%d)",
                            entry.hotkey_id,
                            reg_status,
                        )
                        for r in registered.values():
                            carbon.UnregisterEventHotKey(r)
                        if handler_installed:
                            carbon.RemoveEventHandler(self._handler_ref)
                            handler_installed = False
                            self._handler_ref = ctypes.c_void_p()
                        result_holder["ok"] = False
                        ready_event.set()
                        return
                    registered[entry.hotkey_id] = ref

                self._registered_keys = registered
                self._running = True
                result_holder["ok"] = True
                ready_event.set()

                try:
                    while self._running:
                        out_event = ctypes.c_void_p()
                        ev_status = carbon.ReceiveNextEvent(
                            1,
                            ctypes.byref(event_type),
                            ctypes.c_double(0.1),
                            1,
                            ctypes.byref(out_event),
                        )
                        if ev_status == 0 and out_event.value:
                            carbon.SendEventToEventTarget(out_event, target)
                            carbon.ReleaseEvent(out_event)
                finally:
                    for r in list(self._registered_keys.values()):
                        carbon.UnregisterEventHotKey(r)
                    self._registered_keys.clear()
                    if handler_installed:
                        carbon.RemoveEventHandler(self._handler_ref)
                        handler_installed = False
                        self._handler_ref = ctypes.c_void_p()
                    self._running = False

            self._thread = threading.Thread(
                target=_run, daemon=True, name="MacOSHotkeyListenerThread"
            )
            self._thread.start()
            ready_event.wait(timeout=1.0)
            return result_holder.get("ok", False)

    def stop(self) -> None:
        """ホットキー監視スレッドを停止し、登録済みの全キーを解除する。"""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._c_handler = None
        self._running = False
