# ChalBe

**ChalBe** is an AI-powered, intelligent command-line assistant designed to supercharge your terminal. It integrates with multiple leading AI providers to understand natural language commands, automate complex tasks, and provide intelligent suggestions right where you work.

Stop memorizing arcane flags and syntax. Just tell ChalBe what you want to do.

## Here's a list of the commands and their short descriptions

- **`chal config`**: Configures ChalBe (the CLI tool) with your chosen AI provider, model, and API key.
- **`chal list`**: Generates and executes a shell command to list files based on your natural language intent (e.g., "python files modified today").
- **`chal touch <path>`**: Creates an empty file, similar to the standard `touch` command.
- **`chal delete <path>`**: Safely removes a file or directory with confirmation.
- **`chal copy <src> <dst>`**: Copies a file or directory.
- **`chal move <src> <dst>`**: Moves or renames a file or directory.
- **`chal show <path>`**: Displays file content, with options for showing specific lines (head/tail) or AI-powered summarization.
- **`chal dekh`**: Lists running processes, with an option for AI analysis of the processes.
- **`chal kill <pid>`**: Kills a process by its PID, with confirmation.
- **`chal perfix <error_text>`**: Explains a filesystem permission error and suggests a fix using AI.
- **`chal install <pkg>`**: Gets AI advice on installing a software package and offers to run `apt` install.
- **`chal run <script_path>`**: Executes a script, with an option for AI to predict its behavior and side-effects first.
- **`chal find-nl <intent>`**: Finds files or directories using a natural language description, suggesting and executing a `find` command.
- **`chal net --target <host_or_url>`**: Runs basic network diagnostics (ping, curl) and gets AI-powered advice.
- **`chal envhint <context>`**: Suggests environment variables needed for an application or task using AI.
- **`chal git`**: Generates a conventional commit message for staged git changes using AI.
- **`chal sysinfo`**: Generates a system report (uname, df, free) and provides AI-powered advice.
- **`chal zip <sources...> <dest>`**: Compresses files, with an option for AI advice on the best compression approach.
- **`chal schedule <nl>`**: Creates a cron job from a natural language description and offers to install it.
- **`chal sudo <command>`**: Analyzes a potentially dangerous command with AI before running it with `sudo`.
- **`chal ask <nl>`**: Translates a natural language instruction into a shell command(s) using AI and optionally executes them.
