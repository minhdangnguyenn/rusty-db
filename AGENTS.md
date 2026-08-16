# Global Core Operational Rules for AI Agents

## 1. Safety & Version Control Boundaries (CRITICAL)

- **NO AUTONOMOUS COMMITS OR PUSHES**
  - Never run `git commit` or `git push`.
  - Never modify repository history or publish changes without explicit, line-by-line user approval.
  - Read-only Git commands such as `git status`, `git diff`, and `git log` are allowed.

## 2. Explanation & Transparency Policy

- **EXPLAIN BEFORE ACTING**
  - Before executing a command, refactoring code, or modifying configuration files, clearly explain what will be done and why.
  - For commands with side effects, clearly explain their consequences before running them.
  - Avoid black-box operations.

## 3. Environment & Tooling Constraints

- **RESPECT SYSTEM ENVIRONMENT**
  - The development environment is Arch Linux / CachyOS.
  - Prefer `pacman`, `yay`, or local package files (`.pkg.tar.zst`) where appropriate.
  - Do not assume Debian/Ubuntu tooling such as `apt` is available unless explicitly requested.
  - Do not perform global package installations requiring root privileges unless explicitly requested.
  - Prefer user-local or scoped tooling such as `npx`.

## 4. Code Quality & Verification

- **VERIFY BEFORE CONCLUDING**
  - Check code logic against existing helpers, configuration files, and types before presenting solutions.
  - Do not leave placeholders, broken imports, or incomplete changes.
  - Keep code clean, human-readable, and easy to understand.
  - Use meaningful variable names.
  - Follow the naming conventions already established by the project.
  - For Python, always add type hints for variables.

## 5. Code Comments

- **NO EXPLANATORY COMMENTS IN CODE**
  - Do not insert conversational remarks, meta-commentary, notes directed at the user, or acknowledgement messages into source files.
  - Keep explanations in the chat rather than inside source code comments.