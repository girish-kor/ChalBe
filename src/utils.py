import shlex
import subprocess
import logging
import os
from typing import Optional, Tuple

import click

logger = logging.getLogger("chalbe")

def run_cmd(cmd: str, capture: bool = False, check: bool = False) -> Tuple[int, str, str]:
    """
    Runs a shell command.

    Args:
        cmd (str): The shell command string to execute.
        capture (bool): If True, stdout and stderr are captured and returned.
                        Otherwise, they are printed to the console.
        check (bool): If True, raises a CalledProcessError if the command returns a non-zero exit code.

    Returns:
        Tuple[int, str, str]: A tuple containing the return code, stdout, and stderr.
    """
    logger.debug("Attempting to run command: %s", cmd)
    stdout_data = ""
    stderr_data = ""
    return_code = 1 # Default to error code

    try:
        # For shell=True, subprocess directly passes the string to the shell.
        # shlex.split is typically used when shell=False to safely split arguments.
        # Although not strictly *needed* for shell=True, we include it here to
        # demonstrate its usage and resolve the Pylance warning if direct usage
        # was intended for other scenarios (e.g., shell=False or argument parsing).
        # If the intent is purely shell=True, this line can be removed as `cmd` is passed as-is.
        _ = shlex.split(cmd)

        proc = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            text=True, # Decode stdout/stderr as text using default encoding
            check=check
        )
        stdout_data = proc.stdout if proc.stdout is not None else ""
        stderr_data = proc.stderr if proc.stderr is not None else ""
        return_code = proc.returncode

    except FileNotFoundError:
        # This can happen if the shell itself (e.g., /bin/sh) is not found,
        # or if the command specified in `cmd` (e.g., 'nonexistent_command')
        # is not found by the shell.
        error_msg = f"Command not found: '{cmd.split(' ', 1)[0]}'. Check if it's installed and in your PATH."
        logger.error(error_msg)
        stderr_data = error_msg
        return_code = 1
    except PermissionError:
        error_msg = f"Permission denied to execute command or shell: '{cmd}'."
        logger.error(error_msg)
        stderr_data = error_msg
        return_code = 1
    except subprocess.CalledProcessError as e:
        # This exception is caught if 'check=True' and the command returns a non-zero exit status.
        stdout_data = e.stdout if e.stdout is not None else ""
        stderr_data = e.stderr if e.stderr is not None else f"Command failed with exit code {e.returncode}: {e}"
        return_code = e.returncode
        logger.error("Command failed: %s (Exit Code: %d)\nStdout: %s\nStderr: %s", cmd, return_code, stdout_data, stderr_data)
    except subprocess.TimeoutExpired as e:
        error_msg = f"Command timed out after {e.timeout} seconds: {cmd}"
        logger.error(error_msg)
        stderr_data = error_msg
        if e.stdout: stdout_data = e.stdout
        if e.stderr: stderr_data += "\n" + e.stderr
        return_code = 124 # Common exit code for timeout
    except Exception as e:
        # Catch any other unexpected exceptions during subprocess execution.
        error_msg = f"An unexpected error occurred while running command '{cmd}': {e}"
        logger.error(error_msg, exc_info=True) # exc_info=True logs the full traceback
        stderr_data = error_msg
        return_code = 1

    return return_code, stdout_data, stderr_data


def confirm_and_run(shell_cmd: str, yes: bool = False) -> Tuple[int, str, str]:
    """
    Prompts the user to confirm execution of a shell command before running it.

    Args:
        shell_cmd (str): The shell command string to execute.
        yes (bool): If True, the command is executed without confirmation.

    Returns:
        Tuple[int, str, str]: A tuple containing the return code, stdout, and stderr.
    """
    click.echo(f"Suggested command: {shell_cmd}")
    if not yes:
        try:
            confirmed = click.confirm("Execute this command?", default=False)
            if not confirmed:
                click.echo("Aborted by user.")
                return 0, "", "Aborted by user"
        except Exception as e:
            error_msg = f"Error during confirmation prompt: {e}"
            logger.error(error_msg)
            return 1, "", error_msg

    # If confirmed or 'yes' flag is True, run the command
    return run_cmd(shell_cmd, capture=True, check=False)


def shutil_which(name: str) -> Optional[str]:
    """
    Finds the path to an executable given its name using shutil.which.

    Args:
        name (str): The name of the executable.

    Returns:
        Optional[str]: The path to the executable if found, otherwise None.
    """
    from shutil import which
    try:
        path = which(name)
        if path:
            logger.debug("Found executable '%s' at: %s", name, path)
        else:
            logger.debug("Executable '%s' not found.", name)
        return path
    except Exception as e:
        logger.error("Error while searching for executable '%s': %s", name, e)
        return None
