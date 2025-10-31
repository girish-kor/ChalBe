import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
import importlib
from pathlib import Path
import os
import sys

from chalbe.commands import cli

def mock_load_config_or_exit():
    return "mock_provider", "mock_model", "mock_api_key"

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture(autouse=True)
def mock_load_env():
    """Mocks load_env for all tests to prevent actual file I/O for config."""
    with patch('chalbe.commands.load_env') as mock_env:
        mock_env.return_value = ("test_provider", "test_model", "test_api_key")
        yield mock_env

@pytest.fixture(autouse=True)
def mock_shutil_which():
    """Mocks shutil_which for all tests."""
    with patch('chalbe.commands.shutil_which') as mock_which:
        mock_which.return_value = "/usr/bin/apt" # Default to apt being present
        yield mock_which

@pytest.fixture
def mock_run_cmd():
    """Mocks the run_cmd utility function."""
    with patch('chalbe.commands.run_cmd') as mock_run:
        # Default successful command execution
        mock_run.return_value = (0, "mock output", "mock error")
        yield mock_run

@pytest.fixture
def mock_confirm_and_run():
    """Mocks the confirm_and_run utility function."""
    with patch('chalbe.commands.confirm_and_run') as mock_confirm:
        mock_confirm.return_value = None # It just runs or aborts
        yield mock_confirm

# Mock AI prompt functions
@pytest.fixture(autouse=True)
def mock_ai_prompts():
    mock_ai = MagicMock()
    ai_names = [
        'ai_suggest_navigation', 'ai_summarize_text', 'ai_analyze_processes',
        'ai_explain_permission_error', 'ai_package_advice', 'ai_predict_script',
        'ai_find_command', 'ai_network_diagnostic', 'ai_env_suggestion',
        'ai_git_commit_message', 'ai_system_advice', 'ai_compression_advice',
        'ai_cron_from_nl', 'ai_dryrun_check', 'ai_nl_to_shell'
    ]

    patch_kwargs = {name: getattr(mock_ai, name) for name in ai_names}
    with patch.multiple('chalbe.commands', **patch_kwargs):
        # After patching, build a mapping from name -> patched function in the module
        mod = importlib.import_module('chalbe.commands')
        mapping = {name: getattr(mod, name) for name in ai_names}
        # Set default return values for convenience
        for mock_func in mapping.values():
            mock_func.return_value = "mock AI response"
        yield mapping


# --- Test Cases ---

def test_config_command(runner):
    with patch('chalbe.commands.save_env') as mock_save_env, \
         patch('click.prompt', side_effect=["openai", "gpt-4", "test_key"]), \
         patch('click.Choice'):
        result = runner.invoke(cli, ["config"])
        assert result.exit_code == 0
        assert "Configuration saved successfully." in result.output
        mock_save_env.assert_called_once_with("openai", "gpt-4", "test_key")

def test_config_command_error(runner):
    with patch('chalbe.commands.save_env', side_effect=Exception("Save error")), \
         patch('click.prompt', side_effect=["openai", "gpt-4", "test_key"]), \
         patch('click.Choice'):
        result = runner.invoke(cli, ["config"])
        assert result.exit_code == 1
        assert "Error saving configuration: Save error" in result.output

def test_config_missing_exits(runner, mock_load_env):
    mock_load_env.return_value = (None, None, None)
    result = runner.invoke(cli, ["list", "-i", "some intent"])
    assert result.exit_code == 1
    assert "Error: Missing configuration." in result.output

def test_ls_intel_command_success(runner, mock_ai_prompts, mock_confirm_and_run, mock_load_env):
    mock_ai_prompts['ai_suggest_navigation'].return_value = "ls -l"
    result = runner.invoke(cli, ["list", "-i", "list all files"], input='y\n')
    assert result.exit_code == 0
    assert "Suggested command:\nls -l" in result.output
    mock_ai_prompts['ai_suggest_navigation'].assert_called_once()
    mock_confirm_and_run.assert_called_once_with("ls -l", yes=False)

def test_ls_intel_command_no_suggestion(runner, mock_ai_prompts, mock_confirm_and_run):
    mock_ai_prompts['ai_suggest_navigation'].return_value = None
    result = runner.invoke(cli, ["list", "-i", "list all files"])
    assert result.exit_code == 0
    assert "Error: AI could not suggest a command." in result.output
    mock_confirm_and_run.assert_not_called()

def test_ls_intel_command_yes_flag(runner, mock_ai_prompts, mock_confirm_and_run):
    mock_ai_prompts['ai_suggest_navigation'].return_value = "ls -l"
    result = runner.invoke(cli, ["list", "-i", "list all files", "--yes"])
    assert result.exit_code == 0
    mock_confirm_and_run.assert_called_once_with("ls -l", yes=True)

def test_touch_command_success(runner, tmp_path):
    file_path = tmp_path / "new_file.txt"
    result = runner.invoke(cli, ["touch", str(file_path)])
    assert result.exit_code == 0
    assert f"Successfully touched {file_path}" in result.output
    assert file_path.exists()

def test_touch_command_create_parents(runner, tmp_path):
    nested_path = tmp_path / "dir1" / "dir2" / "new_file.txt"
    result = runner.invoke(cli, ["touch", str(nested_path), "--create-parents"])
    assert result.exit_code == 0
    assert f"Successfully touched {nested_path}" in result.output
    assert nested_path.exists()
    assert nested_path.parent.exists()

def test_touch_command_file_exists(runner, tmp_path):
    file_path = tmp_path / "existing_file.txt"
    file_path.touch()
    result = runner.invoke(cli, ["touch", str(file_path)])
    assert result.exit_code == 0
    assert f"Warning: File already exists at {file_path}." in result.output

def test_touch_command_permission_error(runner, tmp_path):
    # Simulate permission denied by trying to touch in a read-only dir (not easily done with tmp_path)
    # This test might be more effectively done by mocking Path.touch directly
    with patch('pathlib.Path.touch', side_effect=PermissionError("Mock Permission Denied")):
        file_path = tmp_path / "no_permission.txt"
        result = runner.invoke(cli, ["touch", str(file_path)])
        assert result.exit_code == 1
        assert "Error: Permission denied" in result.output

def test_rm_safe_command_success(runner, tmp_path, mock_run_cmd):
    test_file = tmp_path / "file_to_remove.txt"
    test_file.touch()
    # Mock click.confirm to return True for removal
    with patch('click.confirm', return_value=True):
        result = runner.invoke(cli, ["delete", str(test_file)])
        assert result.exit_code == 0
        assert f"Removed {test_file} successfully." in result.output
        mock_run_cmd.assert_called_once_with(f"rm -rf -- '{str(test_file)}'", capture=True)

def test_rm_safe_command_aborted(runner, tmp_path, mock_run_cmd):
    test_file = tmp_path / "file_to_remove.txt"
    test_file.touch()
    with patch('click.confirm', return_value=False):
        result = runner.invoke(cli, ["delete", str(test_file)])
        assert result.exit_code == 0
        assert "Aborted." in result.output
        mock_run_cmd.assert_not_called()

def test_rm_safe_command_yes_flag(runner, tmp_path, mock_run_cmd):
    test_file = tmp_path / "file_to_remove.txt"
    test_file.touch()
    result = runner.invoke(cli, ["delete", str(test_file), "--yes"])
    assert result.exit_code == 0
    assert f"Removed {test_file} successfully." in result.output
    mock_run_cmd.assert_called_once_with(f"rm -rf -- '{str(test_file)}'", capture=True)

def test_rm_safe_command_run_cmd_failure(runner, tmp_path, mock_run_cmd):
    test_file = tmp_path / "file_to_remove.txt"
    test_file.touch()
    mock_run_cmd.return_value = (1, "", "rm error")
    with patch('click.confirm', return_value=True):
        result = runner.invoke(cli, ["delete", str(test_file)])
        assert result.exit_code == 1
        assert f"Error removing {test_file}: rm error" in result.output

def test_cp_command_file_success(runner, tmp_path, mock_run_cmd):
    src_file = tmp_path / "src.txt"
    src_file.touch()
    dst_file = tmp_path / "dst.txt"
    result = runner.invoke(cli, ["copy", str(src_file), str(dst_file)])
    assert result.exit_code == 0
    assert f"Copied {src_file} -> {dst_file} successfully." in result.output
    mock_run_cmd.assert_called_once_with(f"copy -- '{str(src_file)}' '{str(dst_file)}'", capture=True)

def test_cp_command_recursive_success(runner, tmp_path, mock_run_cmd):
    src_dir = tmp_path / "src_dir"
    src_dir.mkdir()
    dst_dir = tmp_path / "dst_dir"
    result = runner.invoke(cli, ["copy", "-r", str(src_dir), str(dst_dir)])
    assert result.exit_code == 0
    assert f"Copied {src_dir} -> {dst_dir} successfully." in result.output
    mock_run_cmd.assert_called_once_with(f"copy -r -- '{str(src_dir)}' '{str(dst_dir)}'", capture=True)

def test_cp_command_source_not_found(runner, tmp_path):
    result = runner.invoke(cli, ["copy", str(tmp_path / "non_existent.txt"), str(tmp_path / "dst.txt")])
    assert result.exit_code == 1
    assert "Error: Source 'non_existent.txt' not found." in result.output

def test_mv_command_success(runner, tmp_path, mock_run_cmd):
    src_file = tmp_path / "old_name.txt"
    src_file.touch()
    dst_file = tmp_path / "new_name.txt"
    result = runner.invoke(cli, ["move", str(src_file), str(dst_file)])
    assert result.exit_code == 0
    assert f"Moved {src_file} -> {dst_file} successfully." in result.output
    mock_run_cmd.assert_called_once_with(f"move -- '{str(src_file)}' '{str(dst_file)}'", capture=True)

def test_mv_command_source_not_found(runner, tmp_path):
    result = runner.invoke(cli, ["move", str(tmp_path / "non_existent.txt"), str(tmp_path / "dst.txt")])
    assert result.exit_code == 1
    assert "Error: Source 'non_existent.txt' not found." in result.output

def test_view_command_cat_success(runner, tmp_path, mock_run_cmd):
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello World")
    mock_run_cmd.return_value = (0, "Hello World", "")
    result = runner.invoke(cli, ["show", str(test_file)])
    assert result.exit_code == 0
    assert "Hello World" in result.output
    mock_run_cmd.assert_called_once_with(f"cat '{str(test_file)}'", capture=True)

def test_view_command_head_success(runner, tmp_path, mock_run_cmd):
    test_file = tmp_path / "test.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3")
    mock_run_cmd.return_value = (0, "Line 1\nLine 2", "")
    result = runner.invoke(cli, ["show", str(test_file), "-n", "2"])
    assert result.exit_code == 0
    assert "Line 1\nLine 2" in result.output
    mock_run_cmd.assert_called_once_with(f"head -n 2 '{str(test_file)}'", capture=True)

def test_view_command_tail_success(runner, tmp_path, mock_run_cmd):
    test_file = tmp_path / "test.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3")
    mock_run_cmd.return_value = (0, "Line 2\nLine 3", "")
    result = runner.invoke(cli, ["show", str(test_file), "-n", "-2"])
    assert result.exit_code == 0
    assert "Line 2\nLine 3" in result.output
    mock_run_cmd.assert_called_once_with(f"tail -n 2 '{str(test_file)}'", capture=True)

def test_view_command_summarize_success(runner, tmp_path, mock_run_cmd, mock_ai_prompts):
    test_file = tmp_path / "test.txt"
    test_file.write_text("Long content for summarization.")
    mock_run_cmd.return_value = (0, "Long content for summarization.", "")
    mock_ai_prompts['ai_summarize_text'].return_value = "AI summary here."
    result = runner.invoke(cli, ["show", str(test_file), "--summarize"])
    assert result.exit_code == 0
    assert "Long content for summarization." in result.output
    assert "--- Summary ---" in result.output
    assert "AI summary here." in result.output
    mock_ai_prompts['ai_summarize_text'].assert_called_once()

def test_view_command_not_a_file(runner, tmp_path):
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    result = runner.invoke(cli, ["show", str(test_dir)])
    assert result.exit_code == 1
    assert f"Error: '{test_dir}' is not a file." in result.output

def test_ps_aux_command_success(runner, mock_run_cmd):
    mock_run_cmd.return_value = (0, "PID USER COMMAND\n1 root init\n", "")
    result = runner.invoke(cli, ["dekh"])
    assert result.exit_code == 0
    assert "PID USER COMMAND" in result.output
    assert "1 root init" in result.output
    mock_run_cmd.assert_called_once_with("ps aux --sort=-%mem", capture=True)

def test_ps_aux_command_analyze(runner, mock_run_cmd, mock_ai_prompts):
    mock_run_cmd.return_value = (0, "PID USER COMMAND\n1 root init\n", "")
    mock_ai_prompts['ai_analyze_processes'].return_value = "AI analysis of processes."
    result = runner.invoke(cli, ["dekh", "--analyze"])
    assert result.exit_code == 0
    assert "AI analysis of processes." in result.output
    mock_ai_prompts['ai_analyze_processes'].assert_called_once()

def test_kill_command_success(runner, mock_run_cmd):
    with patch('click.confirm', return_value=True):
        result = runner.invoke(cli, ["nikal", "123"])
        assert result.exit_code == 0
        assert "Process 123 signaled successfully." in result.output
        mock_run_cmd.assert_called_once_with("nikal  123", capture=True)

def test_kill_command_force(runner, mock_run_cmd):
    with patch('click.confirm', return_value=True):
        result = runner.invoke(cli, ["nikal", "123", "-9"])
        assert result.exit_code == 0
        assert "Process 123 signaled successfully." in result.output
        mock_run_cmd.assert_called_once_with("nikal -9 123", capture=True)

def test_kill_command_yes_flag(runner, mock_run_cmd):
    result = runner.invoke(cli, ["nikal", "123", "--yes"])
    assert result.exit_code == 0
    assert "Process 123 signaled successfully." in result.output
    mock_run_cmd.assert_called_once_with("nikal  123", capture=True)

def test_kill_command_aborted(runner, mock_run_cmd):
    with patch('click.confirm', return_value=False):
        result = runner.invoke(cli, ["nikal", "123"])
        assert result.exit_code == 0
        assert "Aborted." in result.output
        mock_run_cmd.assert_not_called()

def test_explain_perm_command_success(runner, mock_ai_prompts):
    mock_ai_prompts['ai_explain_permission_error'].return_value = "AI explanation of error."
    result = runner.invoke(cli, ["perfix", "Permission denied: /path/to/file"])
    assert result.exit_code == 0
    assert "AI explanation of error." in result.output
    mock_ai_prompts['ai_explain_permission_error'].assert_called_once()

def test_pkg_install_command_advice_only(runner, mock_ai_prompts, mock_shutil_which, mock_run_cmd):
    mock_shutil_which.return_value = None # Simulate no apt
    mock_ai_prompts['ai_package_advice'].return_value = "Install advice from AI."
    result = runner.invoke(cli, ["install", "mypackage"])
    assert result.exit_code == 0
    assert "--- AI Package Advice ---" in result.output
    assert "Install advice from AI." in result.output
    assert "Info: 'apt' not found. Please install manually" in result.output
    mock_ai_prompts['ai_package_advice'].assert_called_once()
    mock_run_cmd.assert_not_called()

def test_pkg_install_command_with_apt_success(runner, mock_ai_prompts, mock_shutil_which, mock_run_cmd):
    mock_shutil_which.return_value = "/usr/bin/apt"
    mock_ai_prompts['ai_package_advice'].return_value = "Install advice from AI."
    mock_run_cmd.side_effect = [(0, "", ""), (0, "", "")] # Simulate update then install success
    with patch('click.confirm', return_value=True):
        result = runner.invoke(cli, ["install", "mypackage"])
        assert result.exit_code == 0
        assert "Install advice from AI." in result.output
        assert "Package 'mypackage' installed successfully." in result.output
        mock_run_cmd.assert_any_call("sudo apt update && sudo apt install -y 'mypackage'", capture=False)

def test_run_script_command_no_predict(runner, tmp_path, mock_run_cmd):
    script_file = tmp_path / "script.sh"
    script_file.write_text("echo 'hello from script'")
    mock_run_cmd.return_value = (0, "hello from script\n", "")
    with patch('click.confirm', return_value=True):
        result = runner.invoke(cli, ["run", str(script_file)])
        assert result.exit_code == 0
        assert "Script executed successfully." in result.output
        mock_run_cmd.assert_called_once_with(f"bash '{str(script_file)}'", capture=False)

def test_run_script_command_predict_and_run(runner, tmp_path, mock_run_cmd, mock_ai_prompts):
    script_file = tmp_path / "script.sh"
    script_file.write_text("echo 'hello from script'")
    mock_ai_prompts['ai_predict_script'].return_value = "AI predicted output."
    mock_run_cmd.return_value = (0, "hello from script\n", "")
    with patch('click.confirm', return_value=True):
        result = runner.invoke(cli, ["run", str(script_file), "--predict"])
        assert result.exit_code == 0
        assert "--- AI Prediction ---" in result.output
        assert "AI predicted output." in result.output
        assert "Script executed successfully." in result.output
        mock_ai_prompts['ai_predict_script'].assert_called_once()
        mock_run_cmd.assert_called_once_with(f"bash '{str(script_file)}'", capture=False)

def test_run_script_command_yes_flag(runner, tmp_path, mock_run_cmd):
    script_file = tmp_path / "script.sh"
    script_file.write_text("echo 'hello from script'")
    mock_run_cmd.return_value = (0, "hello from script\n", "")
    result = runner.invoke(cli, ["run", str(script_file), "--yes"])
    assert result.exit_code == 0
    assert "Script executed successfully." in result.output
    mock_run_cmd.assert_called_once_with(f"bash '{str(script_file)}'", capture=False)


def test_find_nl_command_success(runner, mock_ai_prompts, mock_confirm_and_run):
    mock_ai_prompts['ai_find_command'].return_value = "find . -name '*.py'"
    result = runner.invoke(cli, ["find", "all python files"], input='y\n')
    assert result.exit_code == 0
    assert "Suggested:\nfind . -name '*.py'" in result.output
    mock_ai_prompts['ai_find_command'].assert_called_once()
    mock_confirm_and_run.assert_called_once_with("find . -name '*.py'", yes=False)

def test_find_nl_command_yes_flag(runner, mock_ai_prompts, mock_confirm_and_run):
    mock_ai_prompts['ai_find_command'].return_value = "find . -name '*.py'"
    result = runner.invoke(cli, ["find", "all python files", "--yes"])
    assert result.exit_code == 0
    mock_confirm_and_run.assert_called_once_with("find . -name '*.py'", yes=True)

def test_diag_network_command_success(runner, mock_run_cmd, mock_ai_prompts):
    mock_run_cmd.side_effect = [
        (0, "Ping successful", ""), # ping
        (0, "HTTP/1.1 200 OK", ""), # curl
    ]
    mock_ai_prompts['ai_network_diagnostic'].return_value = "Network seems fine."
    result = runner.invoke(cli, ["net", "-t", "example.com"])
    assert result.exit_code == 0
    assert "--- ping ---" in result.output
    assert "Ping successful" in result.output
    assert "--- curl ---" in result.output
    assert "HTTP/1.1 200 OK" in result.output
    assert "--- AI Network Advice ---" in result.output
    assert "Network seems fine." in result.output
    mock_ai_prompts['ai_network_diagnostic'].assert_called_once()

def test_diag_network_command_ping_fail_curl_success(runner, mock_run_cmd, mock_ai_prompts):
    mock_run_cmd.side_effect = [
        (1, "", "Ping failed"), # ping
        (0, "HTTP/1.1 200 OK", ""), # curl
    ]
    mock_ai_prompts['ai_network_diagnostic'].return_value = "Ping failed, but curl worked."
    result = runner.invoke(cli, ["net", "-t", "example.com"])
    assert result.exit_code == 0
    assert "Error: Ping failed" in result.output
    assert "HTTP/1.1 200 OK" in result.output
    assert "Ping failed, but curl worked." in result.output

def test_env_suggest_command_success(runner, mock_ai_prompts):
    mock_ai_prompts['ai_env_suggestion'].return_value = "export DB_HOST=localhost"
    result = runner.invoke(cli, ["envhint", "database connection"])
    assert result.exit_code == 0
    assert "export DB_HOST=localhost" in result.output
    mock_ai_prompts['ai_env_suggestion'].assert_called_once()

def test_git_msg_command_success(runner, mock_run_cmd, mock_ai_prompts):
    mock_run_cmd.return_value = (0, "M file1.txt\nM file2.py\ndiff ...", "")
    mock_ai_prompts['ai_git_commit_message'].return_value = "feat: Add new features"
    result = runner.invoke(cli, ["git"])
    assert result.exit_code == 0
    assert "--- Suggested commit message ---" in result.output
    assert "feat: Add new features" in result.output
    mock_ai_prompts['ai_git_commit_message'].assert_called_once()
    mock_run_cmd.assert_called_once_with("git diff --staged --name-only && git --no-pager diff --staged", capture=True)

def test_git_msg_command_no_staged_changes(runner, mock_run_cmd):
    mock_run_cmd.return_value = (0, "", "") # No diff output
    result = runner.invoke(cli, ["git"])
    assert result.exit_code == 0
    assert "No staged changes found to generate a commit message." in result.output
    mock_run_cmd.assert_called_once() # Still runs the diff command

def test_sys_report_command_success(runner, mock_run_cmd, mock_ai_prompts):
    mock_run_cmd.side_effect = [
        (0, "Linux hostname ...", ""), # uname
        (0, "Filesystem Size Used Avail Use%", ""), # df
        (0, "total used free ...", ""), # free
    ]
    mock_ai_prompts['ai_system_advice'].return_value = "System looks healthy."
    result = runner.invoke(cli, ["sysinfo"])
    assert result.exit_code == 0
    assert "Linux hostname ..." in result.output
    assert "Filesystem Size Used Avail Use%" in result.output
    assert "total used free ..." in result.output
    assert "--- AI System Advice ---" in result.output
    assert "System looks healthy." in result.output
    mock_ai_prompts['ai_system_advice'].assert_called_once()

def test_sys_report_command_partial_success(runner, mock_run_cmd, mock_ai_prompts):
    mock_run_cmd.side_effect = [
        (0, "Linux hostname ...", ""), # uname success
        (1, "", "df error"), # df fail
        (0, "total used free ...", ""), # free success
    ]
    mock_ai_prompts['ai_system_advice'].return_value = "Partial report advice."
    result = runner.invoke(cli, ["sysinfo"])
    assert result.exit_code == 0
    assert "Warning: Could not get df information." in result.output
    assert "Partial report advice." in result.output
    mock_ai_prompts['ai_system_advice'].assert_called_once()


def test_compress_command_no_sources(runner):
    result = runner.invoke(cli, ["zip", "output.tar.gz"])
    assert result.exit_code == 1
    assert "Error: No source files/directories provided" in result.output

def test_compress_command_success_no_advice(runner, tmp_path, mock_run_cmd):
    src1 = tmp_path / "file1.txt"
    src1.touch()
    dest = tmp_path / "archive.tar.gz"
    mock_run_cmd.return_value = (0, "", "")
    with patch('click.confirm', return_value=True):
        result = runner.invoke(cli, ["zip", str(src1), str(dest)])
        assert result.exit_code == 0
        assert f"Proposed command: tar -czf '{str(dest)}' '{str(src1)}'" in result.output
        assert f"Compression to {dest} completed successfully." in result.output
        mock_run_cmd.assert_called_once_with(f"tar -czf '{str(dest)}' '{str(src1)}'", capture=False)

def test_compress_command_with_advice(runner, tmp_path, mock_run_cmd, mock_ai_prompts):
    src1 = tmp_path / "file1.txt"
    src1.touch()
    dest = tmp_path / "archive.tar.gz"
    mock_ai_prompts['ai_compression_advice'].return_value = "Use tar.gz for this."
    mock_run_cmd.return_value = (0, "", "")
    with patch('click.confirm', return_value=True):
        result = runner.invoke(cli, ["zip", str(src1), str(dest), "--advice"])
        assert result.exit_code == 0
        assert "--- AI Compression Advice ---" in result.output
        assert "Use tar.gz for this." in result.output
        assert f"Compression to {dest} completed successfully." in result.output
        mock_ai_prompts['ai_compression_advice'].assert_called_once()

def test_compress_command_yes_flag(runner, tmp_path, mock_run_cmd):
    src1 = tmp_path / "file1.txt"
    src1.touch()
    dest = tmp_path / "archive.tar.gz"
    mock_run_cmd.return_value = (0, "", "")
    result = runner.invoke(cli, ["zip", str(src1), str(dest), "--yes"])
    assert result.exit_code == 0
    assert f"Compression to {dest} completed successfully." in result.output
    mock_run_cmd.assert_called_once() # Should run without confirmation

def test_cron_from_nl_command_success(runner, mock_ai_prompts, mock_run_cmd):
    mock_ai_prompts['ai_cron_from_nl'].return_value = "0 0 * * * /usr/local/bin/backup.sh"
    mock_run_cmd.return_value = (0, "", "") # crontab update success
    with patch('click.confirm', return_value=True):
        result = runner.invoke(cli, ["schedule", "run backup script daily at midnight"])
        assert result.exit_code == 0
        assert "Suggested Cron line:" in result.output
        assert "0 0 * * * /usr/local/bin/backup.sh" in result.output
        assert "Crontab updated successfully." in result.output
        mock_ai_prompts['ai_cron_from_nl'].assert_called_once()
        mock_run_cmd.assert_called_once() # For crontab -l and crontab -

def test_cron_from_nl_command_no_suggestion(runner, mock_ai_prompts, mock_run_cmd):
    mock_ai_prompts['ai_cron_from_nl'].return_value = None
    result = runner.invoke(cli, ["schedule", "run backup script daily at midnight"])
    assert result.exit_code == 0
    assert "Error: AI could not generate a cron line" in result.output
    mock_run_cmd.assert_not_called()

def test_cron_from_nl_command_install_aborted(runner, mock_ai_prompts, mock_run_cmd):
    mock_ai_prompts['ai_cron_from_nl'].return_value = "0 0 * * * /usr/local/bin/backup.sh"
    with patch('click.confirm', return_value=False):
        result = runner.invoke(cli, ["schedule", "run backup script daily at midnight"])
        assert result.exit_code == 0
        assert "Suggested Cron line:" in result.output
        assert "Crontab updated successfully." not in result.output # Ensure it's not run
        mock_run_cmd.assert_not_called() # No crontab command should be run

def test_admin_check_command_success(runner, mock_ai_prompts, mock_run_cmd):
    mock_ai_prompts['ai_dryrun_check'].return_value = "This command will remove files."
    mock_run_cmd.return_value = (0, "", "") # sudo command success
    with patch('click.confirm', side_effect=[True, True]): # confirm analysis, then confirm execution
        result = runner.invoke(cli, ["sudo", "rm -rf /tmp/test"])
        assert result.exit_code == 0
        assert "--- AI Analysis ---" in result.output
        assert "This command will remove files." in result.output
        assert "Command executed with sudo successfully." in result.output
        mock_ai_prompts['ai_dryrun_check'].assert_called_once()
        mock_run_cmd.assert_called_once_with("sudo rm -rf /tmp/test", capture=False)

def test_admin_check_command_no_ai_analysis_aborted(runner, mock_ai_prompts, mock_run_cmd):
    mock_ai_prompts['ai_dryrun_check'].return_value = None
    with patch('click.confirm', side_effect=[False]): # Abort after no AI analysis
        result = runner.invoke(cli, ["sudo", "rm -rf /tmp/test"])
        assert result.exit_code == 0
        assert "Warning: AI could not provide an analysis" in result.output
        assert "Aborted." in result.output
        mock_run_cmd.assert_not_called()

def test_admin_check_command_no_ai_analysis_run_anyway(runner, mock_ai_prompts, mock_run_cmd):
    mock_ai_prompts['ai_dryrun_check'].return_value = None
    mock_run_cmd.return_value = (0, "", "")
    with patch('click.confirm', side_effect=[True, True]): # Continue after no AI analysis, then run
        result = runner.invoke(cli, ["sudo", "rm -rf /tmp/test"])
        assert result.exit_code == 0
        assert "Warning: AI could not provide an analysis" in result.output
        assert "Command executed with sudo successfully." in result.output
        mock_run_cmd.assert_called_once_with("sudo rm -rf /tmp/test", capture=False)

def test_smart_command_success(runner, mock_ai_prompts):
    mock_ai_prompts['ai_nl_to_shell'].return_value = "ls -la\necho 'Done'"
    result = runner.invoke(cli, ["ask", "list all files and say done"])
    assert result.exit_code == 0
    assert "--- Generated Commands ---" in result.output
    assert "ls -la" in result.output
    assert "echo 'Done'" in result.output
    mock_ai_prompts['ai_nl_to_shell'].assert_called_once()

def test_smart_command_execute_success(runner, mock_ai_prompts, mock_run_cmd):
    mock_ai_prompts['ai_nl_to_shell'].return_value = "ls -la\necho 'Done'"
    mock_run_cmd.side_effect = [(0, "", ""), (0, "", "")] # Both commands succeed
    with patch('click.confirm', side_effect=[True, True]): # Confirm both commands
        result = runner.invoke(cli, ["ask", "list and done", "--execute"])
        assert result.exit_code == 0
        assert "Command 'ls -la' executed successfully." in result.output
        assert "Command 'echo 'Done'' executed successfully." in result.output
        mock_run_cmd.assert_any_call("ls -la", capture=False)
        mock_run_cmd.assert_any_call("echo 'Done'", capture=False)
        assert mock_run_cmd.call_count == 2

def test_smart_command_execute_one_aborted(runner, mock_ai_prompts, mock_run_cmd):
    mock_ai_prompts['ai_nl_to_shell'].return_value = "ls -la\necho 'Done'"
    mock_run_cmd.side_effect = [(0, "", "")] # Only the first command runs
    with patch('click.confirm', side_effect=[True, False]): # Confirm first, abort second
        result = runner.invoke(cli, ["ask", "list and done", "--execute"])
        assert result.exit_code == 0
        assert "Command 'ls -la' executed successfully." in result.output
        assert "Skipping command: echo 'Done'" in result.output
        mock_run_cmd.assert_called_once_with("ls -la", capture=False)

def test_smart_command_no_shell_output(runner, mock_ai_prompts, mock_run_cmd):
    mock_ai_prompts['ai_nl_to_shell'].return_value = ""
    result = runner.invoke(cli, ["ask", "invalid command", "--execute"])
    assert result.exit_code == 0
    assert "Error: AI could not generate any shell commands." in result.output
    mock_run_cmd.assert_not_called()

def test_smart_command_empty_or_comment_lines(runner, mock_ai_prompts, mock_run_cmd):
    mock_ai_prompts['ai_nl_to_shell'].return_value = "\n# This is a comment\n\nls -l\n"
    mock_run_cmd.return_value = (0, "", "")
    with patch('click.confirm', return_value=True):
        result = runner.invoke(cli, ["ask", "just list", "--execute"])
        assert result.exit_code == 0
        assert "Command 'ls -l' executed successfully." in result.output
        # Ensure only 'ls -l' was considered an executable command
        mock_run_cmd.assert_called_once_with("ls -l", capture=False)

def test_smart_command_ai_error(runner, mock_ai_prompts, mock_run_cmd):
    mock_ai_prompts['ai_nl_to_shell'].side_effect = Exception("AI failure")
    result = runner.invoke(cli, ["ask", "something", "--execute"])
    assert result.exit_code == 1
    assert "An unexpected error occurred during ask command generation/execution: AI failure" in result.output
    mock_run_cmd.assert_not_called()
