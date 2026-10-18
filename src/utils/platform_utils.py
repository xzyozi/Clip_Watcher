"""src/utils/platform_utils.py

OSプラットフォーム固有のシステム情報・環境検知ユーティリティ。
"""

from __future__ import annotations

import logging
import subprocess
import sys
from collections.abc import Sequence

logger = logging.getLogger(__name__)


def is_macos_dark_mode() -> bool:
    """macOS のシステム外観がダークモードに設定されているかを判定する。

    macOS (darwin) 以外、またはコマンド実行に失敗した場合は False を返す。
    """
    if sys.platform != "darwin":
        return False

    try:
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True,
            text=True,
            check=False,
            timeout=1,
        )
        return result.stdout.strip().lower() == "dark"
    except Exception:
        return False


def is_legacy_macos_tk() -> bool:
    """macOS かつ Tk 8.6 未満 (Tk 8.5 等) のレガシー描画環境かを判定する。

    macOS 以外、または Tk が 8.6 以上の場合は False を返す。
    """
    if sys.platform != "darwin":
        return False

    try:
        import tkinter as tk

        tk_ver = getattr(tk, "TkVersion", 0.0)
        return isinstance(tk_ver, (int, float)) and tk_ver < 8.6
    except Exception:
        return False


def apply_macos_aqua_appearance(root: object | None = None) -> bool:
    """macOS Cocoa の外観を強制的に NSAppearanceNameAqua (Light/Aqua) に設定する。

    Tk 8.5 などのレガシー環境において、macOS Dark Mode との描画合成不整合を緩和するために
    Python 標準ライブラリ ctypes のみを用いて Objective-C ランタイム (AppKit) を操作する。
    追加の外部パッケージ (pyobjc 等) は一切不要。

    Args:
        root: tkinter のルートウィンドウ (Tk初期化済みであること)

    Returns:
        bool: 適用に成功した場合は True、失敗または macOS 以外の場合は False。
    """
    if sys.platform != "darwin":
        return False

    # Tk が未初期化の状態で NSApplication を触ると、TkpInit による TKApplication
    # サブクラス化と衝突して致命的エラー (SIGABRT) となるため、Tk 初期化済みであることを確認する。
    try:
        import tkinter as tk

        if root is None and getattr(tk, "_default_root", None) is None:
            return False
    except Exception:
        return False

    try:
        import ctypes
        import ctypes.util

        # AppKit フレームワークをロード
        appkit_path = "/System/Library/Frameworks/AppKit.framework/AppKit"
        try:
            ctypes.cdll.LoadLibrary(appkit_path)
        except OSError:
            pass

        objc_lib = ctypes.util.find_library("objc")
        if not objc_lib:
            return False
        objc = ctypes.cdll.LoadLibrary(objc_lib)

        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]

        # 1. NSApplication sharedApplication
        app_class = objc.objc_getClass(b"NSApplication")
        if not app_class:
            return False
        sel_shared = objc.sel_registerName(b"sharedApplication")
        msg_send_app = ctypes.cast(
            objc.objc_msgSend,
            ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p),
        )
        app = msg_send_app(app_class, sel_shared)
        if not app:
            return False

        # 2. NSString stringWithUTF8String: "NSAppearanceNameAqua"
        str_class = objc.objc_getClass(b"NSString")
        sel_str = objc.sel_registerName(b"stringWithUTF8String:")
        msg_send_str = ctypes.cast(
            objc.objc_msgSend,
            ctypes.CFUNCTYPE(
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p
            ),
        )
        aqua_name = msg_send_str(str_class, sel_str, b"NSAppearanceNameAqua")
        if not aqua_name:
            return False

        # 3. NSAppearance appearanceNamed:
        appearance_class = objc.objc_getClass(b"NSAppearance")
        sel_named = objc.sel_registerName(b"appearanceNamed:")
        msg_send_appearance = ctypes.cast(
            objc.objc_msgSend,
            ctypes.CFUNCTYPE(
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
            ),
        )
        aqua_appearance = msg_send_appearance(appearance_class, sel_named, aqua_name)
        if not aqua_appearance:
            return False

        # 4. [app setAppearance: aqua_appearance]
        sel_set_app = objc.sel_registerName(b"setAppearance:")
        msg_send_set = ctypes.cast(
            objc.objc_msgSend,
            ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p),
        )
        msg_send_set(app, sel_set_app, aqua_appearance)

        # 5. 開かれている既存ウィンドウ群に対しても適用
        try:
            sel_windows = objc.sel_registerName(b"windows")
            msg_send_windows = ctypes.cast(
                objc.objc_msgSend,
                ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p),
            )
            windows_array = msg_send_windows(app, sel_windows)
            if windows_array:
                sel_count = objc.sel_registerName(b"count")
                msg_send_count = ctypes.cast(
                    objc.objc_msgSend,
                    ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p),
                )
                count = msg_send_count(windows_array, sel_count)
                sel_object_at_index = objc.sel_registerName(b"objectAtIndex:")
                msg_send_obj = ctypes.cast(
                    objc.objc_msgSend,
                    ctypes.CFUNCTYPE(
                        ctypes.c_void_p,
                        ctypes.c_void_p,
                        ctypes.c_void_p,
                        ctypes.c_ulong,
                    ),
                )
                for i in range(count):
                    win = msg_send_obj(windows_array, sel_object_at_index, i)
                    if win:
                        msg_send_set(win, sel_set_app, aqua_appearance)
        except Exception:
            pass

        return True
    except Exception:
        return False


# プラットフォームごとの推奨フォールバックフォント優先順位
_PLATFORM_FALLBACK_FONTS: dict[str, list[str]] = {
    "darwin": ["Helvetica", "Arial", "San Francisco", "Menlo", "Courier"],
    "win32": ["Segoe UI", "Arial", "Consolas", "Courier New", "MS Gothic"],
    "linux": ["DejaVu Sans", "Liberation Sans", "Ubuntu", "FreeSans", "Helvetica"],
}

_STANDARD_TK_FONTS = frozenset(
    {
        "TkDefaultFont",
        "TkFixedFont",
        "TkMenuFont",
        "TkHeadingFont",
        "TkCaptionFont",
        "TkSmallCaptionFont",
        "TkIconFont",
        "TkTooltipFont",
        "TkTextFont",
        "",
    }
)


def resolve_safe_font_family(
    font_family: str,
    available_families: Sequence[str] | None = None,
) -> str:
    """指定されたフォントファミリが現在の環境で利用可能か検証し、安全なフォント名を返す。

    1. Tk の標準フォント（例: 'TkDefaultFont'）や空文字はそのまま許可する。
    2. 指定されたフォント名が利用可能フォント（available_families または font.families()）
       に存在する場合（大文字小文字の違いを含む）は、そのフォント名を返す。
    3. 存在しない場合（例: Windows 固有の 'FixedSys' が macOS 上で指定された場合等）は、
       プラットフォーム別の推奨フォントまたは 'TkDefaultFont' へ安全にフォールバックする。
    """
    if not font_family or font_family in _STANDARD_TK_FONTS:
        return font_family or "TkDefaultFont"

    # 利用可能フォントリストの解決
    families: Sequence[str] = ()
    if available_families is not None:
        families = available_families
    else:
        try:
            import tkinter.font as tkfont

            families = tkfont.families()
        except Exception:
            # Tk ルート未初期化等の場合は検証できないため、元のフォント名をそのまま返す
            return font_family

    if not families:
        return font_family

    # 大文字小文字を区別しない完全一致チェック
    family_map = {f.lower(): f for f in families}
    if font_family.lower() in family_map:
        return family_map[font_family.lower()]

    # 存在しない場合はプラットフォーム別の推奨フォントへフォールバック
    preferred = _PLATFORM_FALLBACK_FONTS.get(
        sys.platform, _PLATFORM_FALLBACK_FONTS["linux"]
    )
    for pref in preferred:
        if pref.lower() in family_map:
            logger.warning(
                "Font '%s' is not available on %s. Falling back to '%s'.",
                font_family,
                sys.platform,
                family_map[pref.lower()],
            )
            return family_map[pref.lower()]

    logger.warning(
        "Font '%s' is not available on %s and no preferred fallback found. Falling back to 'TkDefaultFont'.",
        font_family,
        sys.platform,
    )
    return "TkDefaultFont"
