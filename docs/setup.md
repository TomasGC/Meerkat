# Setup Guide

Install and configure all required tools to use Meerkat.

---

## 1. Node.js 18+ *(required)*

Required for Claude Code (`npm`) and Node.js/Vue.js project templates.

> Docs: https://nodejs.org/

**macOS**
```bash
brew install node
node --version  # v18+
```

**Windows**
```powershell
winget install OpenJS.NodeJS.LTS
node --version
```

**Linux**
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs
node --version
```

---

## 2. Claude Code *(required)*

> Docs: https://docs.anthropic.com/claude-code

```bash
npm install -g @anthropic-ai/claude-code
```

---

## 3. Python 3.12+ *(required)*

All automation scripts require Python 3.12+.

> Docs: https://docs.python.org/3.12/

**macOS**
```bash
brew install python@3.12
python3 --version  # Python 3.12.x
```

**Windows**
```powershell
winget install Python.Python.3.12
python --version
```

**Linux**
```bash
sudo apt install python3.12 python3.12-venv python3-pip
python3.12 --version
```

---

## 4. Git *(required)*

> Docs: https://git-scm.com/doc

**macOS**
```bash
brew install git
```

**Windows**
```powershell
winget install Git.Git
```

**Linux**
```bash
sudo apt install git
```

---

## 5. uv *(recommended — fast Python package manager)*

> Docs: https://docs.astral.sh/uv/

**macOS / Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

**Windows**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv --version
```

---

## 6. Ollama *(recommended — enables local model delegation)*

Required to use the delegation system (agents, token optimization).

> Docs: https://ollama.com/docs

**macOS / Linux**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama --version
```

**Windows**
```powershell
winget install Ollama.Ollama
# or download: https://ollama.com/download/windows
```

### Pull models

```bash
# Hot tier — preloaded, instant response (<1s)
ollama pull qwen2.5-coder:7b   # Code review, quick fixes
ollama pull llama3.2:3b        # Syntax validation
ollama pull llama-guard3:1b    # Security scan

# Warm tier — on-demand, 5-10s load
ollama pull qwen2.5-coder:14b  # Deep code review

# Cold tier — 30s+, requires 32GB+ RAM
ollama pull llama3.3:70b       # Critical architecture decisions
```

> See `contexts/delegation-strategy.md` for full model routing details.

---

## 7. Python Dependencies

Install script dependencies after cloning:

```bash
cd ~/.claude/scripts

# With uv (recommended)
uv pip install -r requirements.txt

# With pip
pip install -r requirements.txt
```

Verify everything works:
```bash
python -m pytest tests/ -v --maxfail=1
```

---

## Summary

| Tool | Required | Purpose |
|------|----------|---------|
| Node.js 18+ | ✅ | npm + JS/TS project templates |
| Claude Code | ✅ | Core CLI |
| Python 3.12+ | ✅ | Automation scripts |
| Git | ✅ | Version control |
| uv | ⭐ Recommended | Fast package manager |
| Ollama | ⭐ Recommended | Local model delegation |
