# OpenWebUI CLI - Quick Evaluation Prompt

**5-Minute Code Review for OpenWebUI CLI**

---

## Your Task

You are a code reviewer performing a **rapid assessment** of the OpenWebUI CLI project. Focus on the most critical issues that would block alpha/beta release.

**Repository:** `/home/setup/openwebui-cli/`
**RFC:** `/home/setup/openwebui-cli/docs/RFC.md`

---

## Quick Checklist (15 Minutes)

### 1. Does it run? (3 min)

```bash
cd /home/setup/openwebui-cli
pip install -e ".[dev]"

# Test basic commands
openwebui --help
openwebui auth --help
openwebui chat --help
```

**Questions:**
- [ ] Does `openwebui --help` work without errors?
- [ ] Are all command groups present (auth, chat, rag, models, config)?
- [ ] Any import errors or missing dependencies?

---

### 2. Core Functionality Test (5 min)

```bash
# Install and test streaming
openwebui chat send -m llama3.2:latest -p "Count to 10"
```

**Questions:**
- [ ] Does streaming work (tokens appear progressively)?
- [ ] Can you cancel with Ctrl-C?
- [ ] Are errors handled gracefully?

---

### 3. Code Quality Scan (3 min)

```bash
# Run linting
ruff check openwebui_cli

# Run type checking
mypy openwebui_cli

# Check test coverage
pytest tests/ --cov=openwebui_cli
```

**Questions:**
- [ ] Linting: Any critical violations?
- [ ] Type checking: Any errors?
- [ ] Test coverage: Above 60%?

---

### 4. RFC Compliance Quick Check (2 min)

Open `docs/RFC.md` and verify:

**Core Features:**
- [ ] Authentication (login, logout, whoami)
- [ ] Chat (send, streaming)
- [ ] RAG (files, collections)
- [ ] Models (list, info)
- [ ] Config (init, show, profiles)

**Missing Features:**
- [ ] `chat continue` with history?
- [ ] `--system` prompt?
- [ ] Stdin pipe support?
- [ ] `rag search`?
- [ ] Admin commands?

---

### 5. Security Quick Scan (2 min)

Check critical security:

```bash
# Check for vulnerabilities
pip-audit

# Review token storage
grep -r "keyring" openwebui_cli/
```

**Questions:**
- [ ] Are tokens stored in keyring (not plaintext)?
- [ ] Any hardcoded credentials?
- [ ] Any known dependency vulnerabilities?

---

## Quick Assessment Output

**Overall Status:**
- [ ] 🟢 **Ready for Alpha** - Core functionality works, minor issues only
- [ ] 🟡 **Needs Work** - Functional but has significant gaps
- [ ] 🔴 **Not Ready** - Major blockers or broken features

**Top 3 Issues:**
1. [Most critical issue]
2. [Second priority]
3. [Third priority]

**Estimated Time to Alpha-Ready:** __ hours

**Recommendation:**
[Deploy now / Fix top 3 issues first / Needs major refactoring]

---

## Example Output Format

```markdown
# Quick Eval: OpenWebUI CLI v0.1.0

**Status:** 🟡 Needs Work (85% functional)

**Top 3 Issues:**
1. Streaming not implemented - returns full response at once (6h fix)
2. Missing `--system` prompt support (2h fix)
3. Test coverage only 45% (8h to reach 80%)

**Estimated Fix Time:** 16 hours

**Recommendation:** Fix streaming (#1) and deploy alpha. Issues #2-3 can wait for beta.
```

---

**BEGIN QUICK EVAL NOW**
