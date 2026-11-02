from executive_report.cli import main


def test_cli_generates_files(synthetic_dir, tmp_path, capsys):
    code = main(["--data-dir", str(synthetic_dir), "--provider", "offline", "--out", str(tmp_path)])
    assert code == 0
    assert (tmp_path / "report_2018-08.md").exists()
    assert "Report saved" in capsys.readouterr().out


def test_cli_returns_error_code_for_bad_folder(tmp_path, capsys):
    code = main(["--data-dir", str(tmp_path / "missing"), "--provider", "offline"])
    assert code == 1
    assert "File not found" in capsys.readouterr().err
