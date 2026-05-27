# Interactive Session Reference

## Slash Commands

### Session & Context
| Command | Purpose |
|---------|---------|
| `/help` | Show all commands |
| `/compact [focus]` | Compress context to save tokens |
| `/clear` | Wipe conversation history |
| `/context` | Visualize context usage |
| `/cost` | View token usage breakdown |
| `/resume` | Switch to or resume a session |
| `/rewind` | Revert to previous checkpoint |
| `/btw <question>` | Side question (no context cost) |
| `/status` | Version, connectivity, session info |
| `/todos` | List tracked action items |
| `/exit` or `Ctrl+D` | End session |

### Development & Review
| Command | Purpose |
|---------|---------|
| `/review` | Code review of current changes |
| `/security-review` | Security analysis |
| `/plan [description]` | Enter Plan mode |
| `/loop [interval]` | Schedule recurring tasks |
| `/batch` | Auto-create worktrees for parallel changes |

### Configuration & Tools
| Command | Purpose |
|---------|---------|
| `/model [model]` | Switch models mid-session |
| `/effort [level]` | Set reasoning effort |
| `/init` | Create CLAUDE.md |
| `/memory` | Open CLAUDE.md for editing |
| `/config` | Interactive settings |
| `/permissions` | View/update tool permissions |
| `/agents` | Manage subagents |
| `/mcp` | Manage MCP servers |
| `/add-dir` | Add additional working directories |
| `/usage` | Plan limits and rate limit status |
| `/voice` | Push-to-talk voice mode |

### Custom Slash Commands

Create `.claude/commands/<name>.md`:
```markdown
Run the deploy pipeline:
1. Run all tests
2. Build Docker image
3. Push to registry
4. Update $ARGUMENTS environment (default: staging)
```
Usage: `/deploy production` — `$ARGUMENTS` replaces user input.

## Keyboard Shortcuts

### General Controls
| Key | Action |
|-----|--------|
| `Ctrl+C` | Cancel input/generation |
| `Ctrl+D` | Exit session |
| `Ctrl+R` | Reverse search history |
| `Ctrl+B` | Background running task |
| `Ctrl+O` | Transcript mode |
| `Esc Esc` | Rewind/summarize |

### Mode Toggles
| Key | Action |
|-----|--------|
| `Shift+Tab` | Cycle permission modes |
| `Alt+P` | Switch model |
| `Alt+T` | Toggle thinking mode |

### Input Prefixes
| Prefix | Action |
|--------|--------|
| `!` | Execute bash directly (`!npm test`) |
| `@` | Reference files with autocomplete |
| `#` | Quick add to CLAUDE.md memory |
| `/` | Slash commands |

### Pro Tips
- Use `ultrathink` in any prompt for max reasoning effort on that turn
- `\` + `Enter` for quick newline in multi-line input
