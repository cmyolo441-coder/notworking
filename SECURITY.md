# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in ZEDPY/BITTU, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities.
2. Email the maintainer at the address in the repository's git log, or
3. Use GitHub's private vulnerability reporting feature if available.

## What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if any)

## Response Timeline

- **Acknowledgment**: within 48 hours
- **Initial assessment**: within 1 week
- **Fix or mitigation**: depends on severity, but typically within 2 weeks

## Scope

This policy covers:
- The `zedpy` Python package
- The TUI application
- Tool implementations (file operations, shell execution, git commands)
- LLM API communication
- Configuration and secrets handling

## Security Practices

- API keys are loaded from environment variables, never hardcoded in source
- File operations are sandboxed to the project working directory via `safe_path()`
- Shell commands require user approval by default (unless `--yolo` mode)
- Tool results are truncated to prevent context overflow
- Checkpoints are stored locally and should not be committed to version control

## Out of Scope

- The upstream LLM API (opencode.ai) — its security is independent
- Third-party Python packages (textual, requests, etc.)
