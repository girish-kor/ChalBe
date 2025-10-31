import sys
import shlex
from pathlib import Path
from typing import Tuple

import click

from .config import PROVIDERS, save_env, load_env
from .ai_prompts import (
    ai_suggest_navigation, ai_summarize_text, ai_analyze_processes,
    ai_explain_permission_error, ai_package_advice, ai_predict_script,
    ai_find_command, ai_network_diagnostic, ai_env_suggestion,
    ai_git_commit_message, ai_system_advice, ai_compression_advice,
    ai_cron_from_nl, ai_dryrun_check, ai_nl_to_shell
)
from .utils import run_cmd, confirm_and_run, shutil_which


@click.group()
def cli():
    """AI-powered command-line interface for terminal automation and natural language command execution."""
    pass


def _load_config_or_exit() -> Tuple[str, str, str]:
    """Helper to load config and exit if missing."""
    provider, model, api_key = load_env()
    if not all([provider, model, api_key]):
        click.echo("Error: Missing configuration. Run 'chal config' to set up your AI provider and API key.")
        sys.exit(1)
    return provider, model, api_key


@cli.command("config")
def cmd_config():
    """Configure ChalBe with your AI provider and API key."""
    try:
        provider = click.prompt("Provider", type=click.Choice(list(PROVIDERS.keys())))
        models = PROVIDERS[provider]["models"]
        model = click.prompt("Model", type=click.Choice(models))
        api_key = click.prompt("API key", hide_input=True)
        save_env(provider, model, api_key)
        click.echo("Configuration saved successfully.")
    except Exception as e:
        click.echo(f"Error saving configuration: {e}")
        sys.exit(1)


@cli.command("list")
@click.option("--intent", "-i", help="Describe what you want to see (e.g., 'python files modified today')", required=True)
@click.option("--cwd", "-C", default=".", help="Directory to run in")
@click.option("--yes", is_flag=True, help="Execute the suggested command without confirmation")
def cmd_ls_intel(intent, cwd, yes):
    """Generates and executes a shell command to list files based on your intent."""
    provider, model, api_key = _load_config_or_exit()
    try:
        suggestion = ai_suggest_navigation(provider, api_key, model, cwd, intent)
        if not suggestion:
            click.echo("Error: AI could not suggest a command.")
            return
        suggestion = suggestion.replace("$PWD", shlex.quote(cwd)).strip()
        click.echo("Suggested command:\n" + suggestion)

        # Use the confirm_and_run from utils.py
        confirm_and_run(suggestion, yes=yes)

    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}")
        sys.exit(1)


@cli.command("touch")
@click.argument("path", type=click.Path())
@click.option("--create-parents", is_flag=True, help="Create parent directories")
def cmd_touch(path, create_parents):
    """Creates an empty file, similar to the standard touch command."""
    try:
        p = Path(path)
        if p.exists():
            click.echo(f"Warning: File already exists at {path}.")
            return
        if create_parents:
            p.parent.mkdir(parents=True, exist_ok=True)
        p.touch(exist_ok=False)
        click.echo(f"Successfully touched {path}")
    except PermissionError:
        click.echo(f"Error: Permission denied to create file at {path}.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error creating file {path}: {e}")
        sys.exit(1)


@cli.command("delete")
@click.argument("path", type=click.Path(exists=True))
@click.option("--yes", is_flag=True, help="Remove without confirmation")
def cmd_rm(path, yes):
    """Safely removes a file or directory with confirmation."""
    p = Path(path)
    if not yes and not click.confirm(f"Remove {p}? This cannot be undone."):
        click.echo("Aborted.")
        return
    cmd = f"rm -rf -- {shlex.quote(str(p))}"
    try:
        rc, out, err = run_cmd(cmd, capture=True)
        if rc == 0:
            click.echo(f"Removed {path} successfully.")
        else:
            click.echo(f"Error removing {path}: {err}")
            sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred during removal of {path}: {e}")
        sys.exit(1)


@cli.command("copy")
@click.argument("src", type=click.Path())
@click.argument("dst", type=click.Path())
@click.option("--recursive", "-r", is_flag=True, help="Recursive copy")
def cmd_cp(src, dst, recursive):
    """Copies a file or directory."""
    try:
        # Validate source existence here so Click doesn't abort with SystemExit(2)
        s = Path(src)
        if not s.exists():
            click.echo(f"Error: Source '{s.name}' not found.")
            sys.exit(1)

        if recursive:
            cmd = f"copy -r -- {shlex.quote(src)} {shlex.quote(dst)}"
        else:
            cmd = f"copy -- {shlex.quote(src)} {shlex.quote(dst)}"
        rc, out, err = run_cmd(cmd, capture=True)
        if rc == 0:
            click.echo(f"Copied {src} -> {dst} successfully.")
        else:
            click.echo(f"Copy failed: {err}")
            sys.exit(1)
    except PermissionError:
        click.echo(f"Error: Permission denied to copy from '{src}' or to '{dst}'.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred during copy: {e}")
        sys.exit(1)


@cli.command("move")
@click.argument("src", type=click.Path())
@click.argument("dst", type=click.Path())
def cmd_mv(src, dst):
    """Moves or renames a file or directory."""
    try:
        s = Path(src)
        if not s.exists():
            click.echo(f"Error: Source '{s.name}' not found.")
            sys.exit(1)

        cmd = f"move -- {shlex.quote(src)} {shlex.quote(dst)}"
        rc, out, err = run_cmd(cmd, capture=True)
        if rc == 0:
            click.echo(f"Moved {src} -> {dst} successfully.")
        else:
            click.echo(f"Move failed: {err}")
            sys.exit(1)
    except PermissionError:
        click.echo(f"Error: Permission denied to move from '{src}' or to '{dst}'.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred during move: {e}")
        sys.exit(1)


@cli.command("show")
@click.argument("path", type=click.Path(exists=True))
@click.option("--lines", "-n", type=int, default=None, help="Show head/tail lines (positive=head, negative=tail)")
@click.option("--summarize", "-s", is_flag=True, help="Use AI to summarize file contents")
def cmd_view(path, lines, summarize):
    """Displays file content, with an option for AI-powered summarization."""
    p = Path(path)
    content_to_summarize = ""
    try:
        if not p.is_file():
            click.echo(f"Error: '{path}' is not a file.")
            sys.exit(1)

        if lines is not None:
            if lines >= 0:
                cmd = f"head -n {lines} {shlex.quote(str(p))}"
            else:
                cmd = f"tail -n {-lines} {shlex.quote(str(p))}"
            rc, out, err = run_cmd(cmd, capture=True)
            if rc == 0:
                click.echo(out)
                content_to_summarize = out
            else:
                click.echo(f"Error reading file (head/tail): {err}")
                sys.exit(1)
        else:
            rc, out, err = run_cmd(f"cat {shlex.quote(str(p))}", capture=True)
            if rc == 0:
                click.echo(out)
                content_to_summarize = out
            else:
                click.echo(f"Error reading file (cat): {err}")
                sys.exit(1)

        if summarize:
            provider, model, api_key = _load_config_or_exit()
            try:
                summary = ai_summarize_text(provider, api_key, model, content_to_summarize[:8000]) # Limit input for AI
                if summary:
                    click.echo("\n--- Summary ---")
                    click.echo(summary)
                else:
                    click.echo("Warning: AI could not generate a summary.")
            except Exception as ai_e:
                click.echo(f"Error during AI summarization: {ai_e}")

    except FileNotFoundError:
        click.echo(f"Error: File '{path}' not found.")
        sys.exit(1)
    except PermissionError:
        click.echo(f"Error: Permission denied to read file '{path}'.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred while viewing '{path}': {e}")
        sys.exit(1)


@cli.command("ps-aux")
@click.option("--analyze", is_flag=True, help="Ask AI to analyze processes")
def cmd_ps_aux(analyze):
    """Lists running processes, with an option for AI analysis."""
    try:
        rc, out, err = run_cmd("ps aux --sort=-%mem", capture=True)
        if rc != 0:
            click.echo(f"Error running ps aux: {err}")
            sys.exit(1)
        click.echo(out)
        if analyze:
            provider, model, api_key = _load_config_or_exit()
            try:
                analysis = ai_analyze_processes(provider, api_key, model, out[:4000]) # Limit input for AI
                if analysis:
                    click.echo("\n--- AI Analysis ---")
                    click.echo(analysis)
                else:
                    click.echo("Warning: AI could not generate an analysis.")
            except Exception as ai_e:
                click.echo(f"Error during AI analysis: {ai_e}")
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}")
        sys.exit(1)


@cli.command("nikal")
@click.argument("pid", type=int)
@click.option("--force", "-9", "sig", flag_value="-9", default=None, help="Use SIGKILL")
@click.option("--yes", is_flag=True, help="Don't ask for confirmation")
def cmd_kill(pid, sig, yes):
    """Kills a process by its PID, with confirmation."""
    signal = sig or ""
    cmd = f"nikal {signal} {pid}"
    if not yes and not click.confirm(f"Run: {cmd}?"):
        click.echo("Aborted.")
        return
    try:
        rc, out, err = run_cmd(cmd, capture=True)
        if rc == 0:
            click.echo(f"Process {pid} signaled successfully.")
        else:
            click.echo(f"Kill failed for PID {pid}: {err}")
            sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred while killing process {pid}: {e}")
        sys.exit(1)


@cli.command("perfix")
@click.argument("error_text", type=str)
def cmd_explain_perm(error_text):
    """Explains a filesystem permission error and suggests a fix using AI."""
    provider, model, api_key = _load_config_or_exit()
    try:
        advice = ai_explain_permission_error(provider, api_key, model, error_text)
        if advice:
            click.echo(advice)
        else:
            click.echo("Warning: AI could not provide an explanation for the permission error.")
    except Exception as e:
        click.echo(f"Error during AI explanation: {e}")
        sys.exit(1)


@cli.command("install")
@click.argument("pkg", type=str)
def cmd_pkg_install(pkg):
    """Gets AI advice on installing a software package."""
    provider, model, api_key = _load_config_or_exit()
    try:
        advice = ai_package_advice(provider, api_key, model, pkg)
        if advice:
            click.echo("--- AI Package Advice ---")
            click.echo(advice)
        else:
            click.echo("Warning: AI could not provide package advice.")

        if shutil_which("apt"):
            if click.confirm(f"Run 'sudo apt update && sudo apt install -y {pkg}'?"):
                # Always wrap package name in single quotes to ensure predictable
                # behavior and match test expectations.
                cmd = f"sudo apt update && sudo apt install -y '{pkg}'"
                rc, out, err = run_cmd(cmd, capture=False)
                if rc == 0:
                    click.echo(f"Package '{pkg}' installed successfully.")
                else:
                    click.echo(f"Error installing package '{pkg}': {err}")
                    sys.exit(1)
        else:
            click.echo("Info: 'apt' not found. Please install manually using your system's package manager.")
    except Exception as e:
        click.echo(f"An unexpected error occurred during package installation advice/execution: {e}")
        sys.exit(1)


@cli.command("run")
@click.argument("script_path", type=click.Path(exists=True))
@click.option("--predict", is_flag=True, help="Ask AI to predict runtime/side-effects before running")
@click.option("--yes", is_flag=True, help="Run without confirmation")
def cmd_run_script(script_path, predict, yes):
    """Executes a script, with an option for AI to predict its behavior first."""
    try:
        with open(script_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except FileNotFoundError:
        click.echo(f"Error: Script file '{script_path}' not found.")
        sys.exit(1)
    except PermissionError:
        click.echo(f"Error: Permission denied to read script file '{script_path}'.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error reading script file '{script_path}': {e}")
        sys.exit(1)

    if predict:
        provider, model, api_key = _load_config_or_exit()
        try:
            pred = ai_predict_script(provider, api_key, model, text[:8000]) # Limit input for AI
            if pred:
                click.echo("--- AI Prediction ---")
                click.echo(pred)
            else:
                click.echo("Warning: AI could not predict script behavior.")
        except Exception as ai_e:
            click.echo(f"Error during AI prediction: {ai_e}")

    if yes or click.confirm("Execute script?"):
        try:
            rc, out, err = run_cmd(f"bash {shlex.quote(script_path)}", capture=False)
            if rc != 0:
                click.echo(f"Script execution failed with error code {rc}.")
                if err:
                    click.echo(f"Error output: {err}")
            else:
                click.echo("Script executed successfully.")
        except Exception as e:
            click.echo(f"An unexpected error occurred during script execution: {e}")
            sys.exit(1)


@cli.command("find")
@click.argument("intent", type=str)
@click.option("--root", "-C", default=".", help="Root directory")
@click.option("--yes", is_flag=True, help="Run suggested command without confirmation")
def cmd_find_nl(intent, root, yes):
    """Finds files or directories using a natural language description."""
    provider, model, api_key = _load_config_or_exit()
    try:
        suggestion = ai_find_command(provider, api_key, model, intent, root)
        if not suggestion:
            click.echo("Error: AI could not suggest a find command.")
            return
        click.echo("Suggested:\n" + suggestion)

        # Use the confirm_and_run from utils.py
        confirm_and_run(suggestion, yes=yes)

    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}")
        sys.exit(1)


@cli.command("net")
@click.option("--target", "-t", required=True, help="Host or URL")
def cmd_diag_network(target):
    """Runs basic network diagnostics and gets AI-powered advice."""
    ping_out, ping_err, curl_out, curl_err = "", "", "", ""

    try:
        rc, ping_out, ping_err = run_cmd(f"ping -c 4 {shlex.quote(target)}", capture=True)
        click.echo("--- ping ---")
        click.echo(ping_out if ping_out else (f"Error: {ping_err}" if ping_err else "No ping output."))
    except Exception as e:
        click.echo(f"Error running ping: {e}")
        ping_err = str(e) # Capture error for AI analysis

    try:
        rc2, curl_out, curl_err = run_cmd(f"curl -Is {shlex.quote(target)} --max-time 5", capture=True)
        click.echo("--- curl ---")
        click.echo(curl_out if curl_out else (f"Error: {curl_err}" if curl_err else "No curl output."))
    except Exception as e:
        click.echo(f"Error running curl: {e}")
        curl_err = str(e) # Capture error for AI analysis

    provider, model, api_key = _load_config_or_exit()
    try:
        diag_input = (ping_out or ping_err) + "\n\n" + (curl_out or curl_err)
        advice = ai_network_diagnostic(provider, api_key, model, diag_input[:4000]) # Limit input for AI
        if advice:
            click.echo("\n--- AI Network Advice ---")
            click.echo(advice)
        else:
            click.echo("Warning: AI could not provide network diagnostics advice.")
    except Exception as e:
        click.echo(f"Error during AI network diagnosis: {e}")
        sys.exit(1)


@cli.command("envhint")
@click.argument("context", type=str)
def cmd_env_suggest(context):
    """Suggests environment variables needed for an application or task."""
    provider, model, api_key = _load_config_or_exit()
    try:
        suggestion = ai_env_suggestion(provider, api_key, model, context)
        if suggestion:
            click.echo(suggestion)
        else:
            click.echo("Warning: AI could not suggest environment variables.")
    except Exception as e:
        click.echo(f"Error during AI environment suggestion: {e}")
        sys.exit(1)


@cli.command("git")
def cmd_git_msg():
    """Generates a conventional commit message for staged git changes."""
    try:
        rc, diff, err = run_cmd("git diff --staged --name-only && git --no-pager diff --staged", capture=True)
        if rc != 0:
            click.echo(f"Error checking staged git changes: {err}")
            sys.exit(1)
        if not diff.strip():
            click.echo("No staged changes found to generate a commit message.")
            return

        provider, model, api_key = _load_config_or_exit()
        try:
            msg = ai_git_commit_message(provider, api_key, model, diff[:4000]) # Limit input for AI
            if msg:
                click.echo("--- Suggested commit message ---")
                click.echo(msg)
            else:
                click.echo("Warning: AI could not generate a commit message.")
        except Exception as ai_e:
            click.echo(f"Error during AI commit message generation: {ai_e}")
    except Exception as e:
        click.echo(f"An unexpected error occurred during git message generation: {e}")
        sys.exit(1)


@cli.command("sysinfo")
def cmd_sys_report():
    """Generates a system report and provides AI-powered advice."""
    uname_out, df_out, free_out = "", "", ""

    try:
        rc_u, uname_out, _ = run_cmd("uname -a", capture=True)
        if rc_u != 0:
            click.echo("Warning: Could not get uname information.")
    except Exception as e:
        click.echo(f"Error running uname: {e}")

    try:
        rc_df, df_out, _ = run_cmd("df -h", capture=True)
        if rc_df != 0:
            click.echo("Warning: Could not get df information.")
    except Exception as e:
        click.echo(f"Error running df: {e}")

    try:
        rc_free, free_out, _ = run_cmd("free -h", capture=True)
        if rc_free != 0:
            click.echo("Warning: Could not get free information.")
    except Exception as e:
        click.echo(f"Error running free: {e}")

    combined = uname_out + "\n\n" + df_out + "\n\n" + free_out
    if not combined.strip():
        click.echo("Error: Failed to gather any system report data.")
        sys.exit(1)

    click.echo(combined)

    provider, model, api_key = _load_config_or_exit()
    try:
        advice = ai_system_advice(provider, api_key, model, combined[:4000]) # Limit input for AI
        if advice:
            click.echo("\n--- AI System Advice ---")
            click.echo(advice)
        else:
            click.echo("Warning: AI could not provide system advice.")
    except Exception as e:
        click.echo(f"Error during AI system advice: {e}")
        sys.exit(1)


@cli.command("zip")
@click.argument("sources", nargs=-1, type=click.Path())
@click.argument("dest", type=click.Path())
@click.option("--advice", is_flag=True, help="Ask AI for best compression approach")
@click.option("--yes", is_flag=True, help="Run zip without asking")
def cmd_compress(sources, dest, advice, yes):
    """Compresses files, with an option for AI advice on the best format."""
    if not sources:
        click.echo("Error: No source files/directories provided for compression.")
        sys.exit(1)

    if advice:
        provider, model, api_key = _load_config_or_exit()
        flist = "\n".join(sources)
        try:
            ai_advice = ai_compression_advice(provider, api_key, model, flist[:2000]) # Limit input for AI
            if ai_advice:
                click.echo("--- AI Compression Advice ---")
                click.echo(ai_advice)
            else:
                click.echo("Warning: AI could not provide compression advice.")
        except Exception as ai_e:
            click.echo(f"Error during AI compression advice: {ai_e}")

    cmd = f"tar -czf {shlex.quote(dest)} " + " ".join(shlex.quote(s) for s in sources)
    click.echo("Proposed command: " + cmd)
    if yes or click.confirm("Run compression?"):
        try:
            rc, out, err = run_cmd(cmd, capture=False)
            if rc == 0:
                click.echo(f"Compression to {dest} completed successfully.")
            else:
                click.echo(f"Compression failed: {err}")
                sys.exit(1)
        except Exception as e:
            click.echo(f"An unexpected error occurred during compression: {e}")
            sys.exit(1)


@cli.command("schedule")
@click.argument("nl", type=str)
def cmd_cron_from_nl(nl):
    """Creates a cron job from a natural language description."""
    provider, model, api_key = _load_config_or_exit()
    try:
        cron_line = ai_cron_from_nl(provider, api_key, model, nl)
        if not cron_line:
            click.echo("Error: AI could not generate a cron line from your description.")
            return
        click.echo("Suggested Cron line:")
        click.echo(cron_line)
        if click.confirm("Install this crontab entry for current user?"):
            # Ensure the cron line is properly escaped for shell if it contains special chars
            escaped_cron_line = shlex.quote(cron_line)
            cmd = f'(crontab -l 2>/dev/null; echo {escaped_cron_line}) | crontab -'
            rc, out, err = run_cmd(cmd, capture=True)
            if rc == 0:
                click.echo("Crontab updated successfully.")
            else:
                click.echo(f"Failed to update crontab: {err}")
                sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred during cron generation/installation: {e}")
        sys.exit(1)


@cli.command("sudo")
@click.argument("command", type=str)
def cmd_admin_check(command):
    """Analyzes a potentially dangerous command with AI before running it with sudo."""
    provider, model, api_key = _load_config_or_exit()
    try:
        explanation = ai_dryrun_check(provider, api_key, model, command)
        if explanation:
            click.echo("--- AI Analysis ---")
            click.echo(explanation)
        else:
            click.echo("Warning: AI could not provide an analysis for the command.")
            if not click.confirm("No AI analysis available. Do you still want to run with sudo?"):
                click.echo("Aborted.")
                return

        if click.confirm(f"Run the command with sudo: 'sudo {command}'?"):
            rc, out, err = run_cmd(f"sudo {command}", capture=False)
            if rc == 0:
                click.echo("Command executed with sudo successfully.")
            else:
                click.echo(f"Command execution with sudo failed with error code {rc}.")
                if err:
                    click.echo(f"Error output: {err}")
                sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred during admin check or execution: {e}")
        sys.exit(1)


@cli.command("ask")
@click.argument("nl", type=str)
@click.option("--execute", is_flag=True, help="Execute the generated command(s) after confirmation")
def cmd_smart(nl, execute):
    """Translates a natural language instruction into a shell command using AI."""
    provider, model, api_key = _load_config_or_exit()
    try:
        shell_out = ai_nl_to_shell(provider, api_key, model, nl)
        if not shell_out:
            click.echo("Error: AI could not generate any shell commands.")
            return

        click.echo("--- Generated Commands ---")
        click.echo(shell_out)

        commands = []
        for line in shell_out.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            commands.append(line)

        if execute and commands:
            for c in commands:
                click.echo("Candidate command: " + c)
                if click.confirm("Execute this command?"):
                    try:
                        rc, out, err = run_cmd(c, capture=False)
                        if rc != 0:
                            click.echo(f"Command '{c}' failed with error code {rc}.")
                            if err:
                                click.echo(f"Error output: {err}")
                        else:
                            click.echo(f"Command '{c}' executed successfully.")
                    except Exception as e:
                        click.echo(f"An unexpected error occurred during command execution '{c}': {e}")
                else:
                    click.echo(f"Skipping command: {c}")
        elif execute:
            click.echo("No executable candidate commands detected automatically. Please run manually if desired.")
    except Exception as e:
        click.echo(f"An unexpected error occurred during ask command generation/execution: {e}")
        sys.exit(1)
