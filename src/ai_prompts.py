from .ai_client import generate_content


def ai_suggest_navigation(provider: str, api_key: str, model: str, cwd: str, intent: str) -> str:
    prompt = (
        f"You are a shell assistant. Current working directory: {cwd}\n"
        f"User intent: {intent}\n"
        "Provide a single safe POSIX shell command (no explanations) to list files or filter results to satisfy the intent."
    )
    return generate_content(provider, api_key, model, prompt).strip()


def ai_suggest_filename(provider: str, api_key: str, model: str, context: str, purpose: str) -> str:
    prompt = (
        f"You are a naming assistant. Files/folders context: {context}\n"
        f"Purpose: {purpose}\n"
        "Suggest one concise filename (no path), one word or hyphenated, lower-case."
    )
    return generate_content(provider, api_key, model, prompt).strip().splitlines()[0]


def ai_summarize_text(provider: str, api_key: str, model: str, text: str, max_sentences: int = 3) -> str:
    prompt = (
        f"Summarize the text below in {max_sentences} sentences. Be concise.\n\nText:\n{text}"
    )
    return generate_content(provider, api_key, model, prompt).strip()


def ai_analyze_processes(provider: str, api_key: str, model: str, ps_output: str) -> str:
    prompt = (
        "Analyze the following `ps aux` output for anomalies or resource issues. "
        "List up to 5 processes to investigate with a short reason each.\n\n"
        f"{ps_output}"
    )
    return generate_content(provider, api_key, model, prompt).strip()


def ai_explain_permission_error(provider: str, api_key: str, model: str, error_text: str) -> str:
    prompt = (
        "A user encountered this filesystem permission error. Explain the cause and give exact shell commands "
        "to fix it safely (one command per line). If unsafe, suggest a safe alternative.\n\nError:\n" + error_text
    )
    return generate_content(provider, api_key, model, prompt).strip()


def ai_package_advice(provider: str, api_key: str, model: str, package_name: str) -> str:
    prompt = (
        f"Provide recommended package manager commands to install '{package_name}' "
        "on Debian/Ubuntu (apt), CentOS/RHEL (yum/dnf), and macOS (brew). Also list common dependency issues."
    )
    return generate_content(provider, api_key, model, prompt).strip()


def ai_predict_script(provider: str, api_key: str, model: str, script_text: str) -> str:
    prompt = (
        "Given this shell script or program, estimate likely runtime, resource usage, and potential side effects. "
        "Be concise and mention dangerous operations (file deletion, network calls, systemctl, etc.).\n\n"
        f"{script_text}"
    )
    return generate_content(provider, api_key, model, prompt).strip()


def ai_find_command(provider: str, api_key: str, model: str, intent: str, root: str = ".") -> str:
    prompt = (
        f"Generate a safe find/grep command rooted at {root} that matches this intent: {intent}. "
        "Return a single shell command only."
    )
    return generate_content(provider, api_key, model, prompt).strip()


def ai_network_diagnostic(provider: str, api_key: str, model: str, diag_text: str) -> str:
    prompt = (
        "Diagnose network issue given the following diagnostic output (ping/curl/ss/iptables). "
        "Provide next troubleshooting commands to try and likely causes.\n\n" + diag_text
    )
    return generate_content(provider, api_key, model, prompt).strip()


def ai_env_suggestion(provider: str, api_key: str, model: str, app_context: str) -> str:
    prompt = (
        f"Given this application/context: {app_context}, suggest environment variables and export commands "
        "needed to run it locally. Provide commands only, one per line."
    )
    return generate_content(provider, api_key, model, prompt).strip()


def ai_git_commit_message(provider: str, api_key: str, model: str, diff_text: str) -> str:
    prompt = (
        "Generate a concise, conventional commit message (subject + 1-line body) for this diff. Use present tense.\n\n"
        f"{diff_text}"
    )
    return generate_content(provider, api_key, model, prompt).strip()


def ai_system_advice(provider: str, api_key: str, model: str, sys_text: str) -> str:
    prompt = "Analyze system status and give recommendations (short) based on the following:\n\n" + sys_text
    return generate_content(provider, api_key, model, prompt).strip()


def ai_compression_advice(provider: str, api_key: str, model: str, file_list_text: str) -> str:
    prompt = (
        "For these files and types, recommend compression format(s) and commands to maximize space savings while "
        "balancing decompression speed. Files:\n\n" + file_list_text
    )
    return generate_content(provider, api_key, model, prompt).strip()


def ai_cron_from_nl(provider: str, api_key: str, model: str, nl: str) -> str:
    prompt = f"Convert this natural language schedule into a valid crontab entry: {nl}. Return only the crontab line."
    return generate_content(provider, api_key, model, prompt).strip()


def ai_dryrun_check(provider: str, api_key: str, model: str, command: str) -> str:
    prompt = (
        "Analyze if the following shell command is safe to run and list its exact effects. "
        "If it may be destructive, propose a safe dry-run alternative.\n\n" + command
    )
    return generate_content(provider, api_key, model, prompt).strip()


def ai_nl_to_shell(provider: str, api_key: str, model: str, nl: str) -> str:
    prompt = (
        "Translate this instruction into a single, safe POSIX shell command. If multiple are needed, "
        "explain in comments and provide the commands. Prefer non-destructive options. Instruction:\n\n" + nl
    )
    return generate_content(provider, api_key, model, prompt).strip()
