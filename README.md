# ChaiHub Telegram Control

This repository contains a minimal human-in-the-loop control system driven by Telegram.

## Quick start

1. Create a Telegram bot and obtain the bot token.
2. Identify your Telegram user ID (the only authorized user).
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the bot:

```bash
export TELEGRAM_BOT_TOKEN=your-token
export AUTHORIZED_USER_ID=123456789
python -m chaihub_control.main
```

## Usage

- `/run <instruction>` injects a new prompt and interrupts the current plan.
- `/status` returns the current goal, action, and pending approvals.
- `/pause` pauses execution.
- `/resume` resumes execution.
- `/stop` halts execution immediately.

Prefix a command with `cmd:` to execute it after explicit approval, e.g.:

```
/run cmd: echo "hello"
```

All approvals use inline buttons.

## Logging

Logs are appended to `logs/control.log` by default.
