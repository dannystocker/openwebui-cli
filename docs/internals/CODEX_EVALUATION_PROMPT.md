# OpenWebUI CLI - Comprehensive Code Evaluation Prompt

**Use this prompt with Claude, GPT-4, or any LLM code assistant to perform a thorough evaluation of the OpenWebUI CLI implementation.**

---

## Your Mission

You are an expert code reviewer evaluating the **OpenWebUI CLI** project. Your task is to perform a comprehensive technical assessment covering architecture, code quality, RFC compliance, security, testing, and production readiness.

**Repository:** https://github.com/dannystocker/openwebui-cli
**Local Path:** `/home/setup/openwebui-cli/`
**RFC Document:** `/home/setup/openwebui-cli/docs/RFC.md`
**Current Status:** v0.1.0 MVP - Alpha development

---

## Evaluation Framework

Assess the implementation across 10 critical dimensions, providing both qualitative analysis and quantitative scores (0-10 scale).

---

## 1. ARCHITECTURE & DESIGN QUALITY

### Assessment Criteria

**Modularity (0-10):**
- [ ] Clear separation of concerns (commands, client, config, errors)
- [ ] Minimal coupling between modules
- [ ] Appropriate abstraction levels
- [ ] Extensibility for future features

**Code Structure (0-10):**
- [ ] Logical file organization (package layout)
- [ ] Consistent naming conventions
- [ ] Appropriate use of OOP vs functional patterns
- [ ] Dependencies are well-managed (pyproject.toml)

**Error Handling (0-10):**
- [ ] Comprehensive exception handling
- [ ] Meaningful error messages
- [ ] Proper exit codes (0-5 defined)
- [ ] Graceful degradation

**Tasks:**
1. Map the directory structure - is it intuitive?
2. Check `openwebui_cli/` package layout - any red flags?
3. Review `errors.py` - comprehensive coverage?
4. Assess `http_client.py` - proper abstraction?

**Score: __/30**

---

## 2. RFC COMPLIANCE (v1.2)

### Reference: `/home/setup/openwebui-cli/docs/RFC.md`

**Core Features Implemented (0-10):**
- [ ] Authentication (login, logout, whoami, token storage)
- [ ] Chat (send, streaming, continue conversation)
- [ ] RAG (files upload, collections, search)
- [ ] Models (list, info)
- [ ] Config (init, show, profiles)
- [ ] Admin commands (stats, diagnostics)

**22-Step Implementation Checklist (0-10):**
Cross-reference the RFC's implementation checklist:
1. Are all 22 steps addressed?
2. Which steps are incomplete?
3. Are there deviations from the RFC design?

**CLI Interface Match (0-10):**
Compare actual commands vs RFC specification:
```bash
# Run these commands and verify against RFC
openwebui --help
openwebui auth --help
openwebui chat --help
openwebui rag --help
openwebui models --help
openwebui config --help
openwebui admin --help
```

**Tasks:**
1. Read RFC.md thoroughly
2. Check each command group exists
3. Verify arguments match RFC specification
4. Identify missing features

**Score: __/30**

---

## 3. CODE QUALITY & BEST PRACTICES

### Python Standards (0-10)

**Type Hints:**
```bash
mypy openwebui_cli --strict
```
- [ ] 100% type coverage on public APIs?
- [ ] Proper use of Optional, Union, Generic?
- [ ] Any mypy errors/warnings?

**Code Style:**
```bash
ruff check openwebui_cli
```
- [ ] PEP 8 compliant?
- [ ] Consistent formatting?
- [ ] Any linting violations?

**Documentation:**
- [ ] Docstrings on all public functions/classes?
- [ ] Docstrings follow Google or NumPy style?
- [ ] Inline comments where necessary?

### Security Best Practices (0-10)

**Authentication Storage:**
- [ ] Tokens stored securely (keyring integration)?
- [ ] No hardcoded credentials?
- [ ] Proper handling of secrets (env vars, config)?

**Input Validation:**
- [ ] User inputs sanitized?
- [ ] API responses validated before use?
- [ ] File paths properly validated (no path traversal)?

**Dependencies:**
```bash
pip-audit  # Check for known vulnerabilities
```
- [ ] All dependencies up-to-date?
- [ ] No known CVEs?

### Performance (0-10)

**Efficiency:**
- [ ] Streaming properly implemented (not buffering entire response)?
- [ ] No unnecessary API calls?
- [ ] Appropriate use of caching?

**Resource Management:**
- [ ] File handles properly closed?
- [ ] HTTP connections reused (session)?
- [ ] Memory leaks avoided?

**Tasks:**
1. Run `mypy openwebui_cli --strict` - capture output
2. Run `ruff check openwebui_cli` - any violations?
3. Check `auth.py` - how are tokens stored?
4. Review `chat.py` - is streaming efficient?

**Score: __/30**

---

## 4. FUNCTIONAL COMPLETENESS

### Core Workflows (0-10)

Test these end-to-end workflows:

**Workflow 1: First-time Setup**
```bash
openwebui config init
openwebui auth login  # Interactive
openwebui auth whoami
```
- [ ] Config created at correct XDG path?
- [ ] Login prompts for username/password?
- [ ] Token stored securely in keyring?
- [ ] Whoami displays user info?

**Workflow 2: Chat (Streaming)**
```bash
openwebui chat send -m llama3.2:latest -p "Count to 10"
```
- [ ] Streaming displays tokens as they arrive?
- [ ] Ctrl-C cancels gracefully?
- [ ] Final response saved to history?

**Workflow 3: RAG Pipeline**
```bash
openwebui rag files upload document.pdf
openwebui rag collections create "Test Docs"
openwebui chat send -m llama3.2:latest -p "Summarize doc" --file <ID>
```
- [ ] File uploads successfully?
- [ ] Collection created?
- [ ] Chat retrieves RAG context?

### Edge Cases (0-10)

Test error handling:
- [ ] Invalid credentials (401)?
- [ ] Network timeout (connection refused)?
- [ ] Invalid model name (404)?
- [ ] Malformed JSON response?
- [ ] Disk full during file upload?

### Missing Features (0-10)

RFC features NOT yet implemented:
- [ ] `chat continue` with conversation history?
- [ ] `--system` prompt support?
- [ ] Stdin pipe support (`cat prompt.txt | openwebui chat send`)?
- [ ] `--history-file` loading?
- [ ] `rag search` semantic search?
- [ ] `admin stats` and `admin diagnostics`?

**Tasks:**
1. Install CLI: `pip install -e ".[dev]"`
2. Run Workflow 1, 2, 3 - document results
3. Test 3+ error scenarios - capture behavior
4. List ALL missing features from RFC

**Score: __/30**

---

## 5. API ENDPOINT ACCURACY

### Verify Against OpenWebUI Source

**Critical Endpoints:**
| Command | Expected Endpoint | Actual Endpoint | Match? |
|---------|-------------------|-----------------|--------|
| auth login | POST /api/v1/auths/signin | ??? | ? |
| auth whoami | GET /api/v1/auths/ | ??? | ? |
| models list | GET /api/models | ??? | ? |
| chat send | POST /api/v1/chat/completions | ??? | ? |
| rag files upload | POST /api/v1/files/ | ??? | ? |
| rag collections list | GET /api/v1/knowledge/ | ??? | ? |

**Tasks:**
1. Read `openwebui_cli/commands/*.py` files
2. Extract API endpoints from each command
3. Cross-reference with OpenWebUI source (if available)
4. Flag any mismatches

**Score: __/10**

---

## 6. TESTING & VALIDATION

### Test Coverage (0-10)

```bash
pytest tests/ -v --cov=openwebui_cli --cov-report=term-missing
```

**Coverage Metrics:**
- [ ] Overall coverage: ___%
- [ ] `auth.py` coverage: ___%
- [ ] `chat.py` coverage: ___%
- [ ] `http_client.py` coverage: ___%
- [ ] `config.py` coverage: ___%

**Target:** >80% coverage for production-ready CLI

### Test Quality (0-10)

Review `tests/` directory:
- [ ] Unit tests exist for all command groups?
- [ ] Integration tests with mocked API?
- [ ] Error scenario tests?
- [ ] Fixtures for common test data?
- [ ] Clear test naming (test_*_should_*)?

### CI/CD (0-10)

Check for automation:
- [ ] GitHub Actions workflow exists?
- [ ] Tests run on every commit?
- [ ] Linting/type checking in CI?
- [ ] Automated releases?

**Tasks:**
1. Run pytest with coverage - capture report
2. Review test files - assess quality
3. Check `.github/workflows/` for CI config

**Score: __/30**

---

## 7. DOCUMENTATION QUALITY

### User-Facing Docs (0-10)

**README.md:**
- [ ] Clear installation instructions?
- [ ] Comprehensive usage examples?
- [ ] Configuration file documented?
- [ ] Exit codes explained?
- [ ] Links to RFC and contributing guide?

**CLI Help Text:**
```bash
openwebui --help
openwebui chat --help
```
- [ ] Help text is clear and actionable?
- [ ] Examples provided in `--help`?
- [ ] All arguments documented?

### Developer Docs (0-10)

**RFC.md:**
- [ ] Design rationale explained?
- [ ] Architecture diagrams (if applicable)?
- [ ] Implementation checklist?
- [ ] API endpoint mapping?

**CONTRIBUTING.md:**
- [ ] Development setup guide?
- [ ] Code style guidelines?
- [ ] Pull request process?

### Code Comments (0-10)

- [ ] Complex logic explained with comments?
- [ ] TODOs/FIXMEs documented?
- [ ] API contract explained in docstrings?

**Tasks:**
1. Read README.md - rate clarity (0-10)
2. Run `--help` for all commands - rate usefulness
3. Review RFC.md for completeness

**Score: __/30**

---

## 8. USER EXPERIENCE

### CLI Ergonomics (0-10)

**Intuitiveness:**
- [ ] Command names are self-explanatory?
- [ ] Argument flags follow conventions (`-m` for model)?
- [ ] Consistent flag naming across commands?

**Output Formatting:**
- [ ] Readable table output (models list)?
- [ ] Colored output for errors/success?
- [ ] Progress indicators for long operations?

**Interactive Features:**
- [ ] Password input hidden (getpass)?
- [ ] Confirmations for destructive actions?
- [ ] Autocomplete support (argcomplete)?

### Error Messages (0-10)

Test error scenarios and rate messages:
```bash
# Example: Invalid credentials
openwebui auth login  # Enter wrong password
```

**Error Message Quality:**
- [ ] Clear description of what went wrong?
- [ ] Actionable suggestions ("Try: openwebui auth login")?
- [ ] Proper exit codes?
- [ ] No stack traces shown to users (unless --debug)?

### Performance Perception (0-10)

- [ ] Startup time <500ms?
- [ ] Streaming feels responsive (<250ms first token)?
- [ ] No noticeable lag in interactive prompts?

**Tasks:**
1. Use CLI for 5+ commands - rate intuitiveness
2. Trigger 3+ errors - rate message quality
3. Time startup: `time openwebui --help`

**Score: __/30**

---

## 9. PRODUCTION READINESS

### Configuration Management (0-10)

**Config File:**
- [ ] XDG-compliant paths (Linux/macOS)?
- [ ] Windows support (%APPDATA%)?
- [ ] Profile switching works?
- [ ] Environment variable overrides?

**Deployment:**
- [ ] `pyproject.toml` properly configured for PyPI?
- [ ] Dependencies pinned with version ranges?
- [ ] Entry point (`openwebui` command) works?

### Logging & Debugging (0-10)

- [ ] `--verbose` or `--debug` flag?
- [ ] Logs to file (optional)?
- [ ] Request/response logging (for debugging)?
- [ ] No sensitive data in logs?

### Compatibility (0-10)

**Python Versions:**
```bash
# Check pyproject.toml
requires-python = ">=3.X"
```
- [ ] Minimum Python version documented?
- [ ] Tested on Python 3.9, 3.10, 3.11, 3.12?

**Operating Systems:**
- [ ] Linux tested?
- [ ] macOS tested?
- [ ] Windows tested?

**Tasks:**
1. Check config file creation on your OS
2. Test profile switching
3. Review pyproject.toml dependencies

**Score: __/30**

---

## 10. SECURITY AUDIT

### Threat Model (0-10)

**Authentication:**
- [ ] Token storage uses OS keyring (not plaintext)?
- [ ] Tokens expire and refresh?
- [ ] Session management secure?

**Input Validation:**
- [ ] Command injection prevented?
- [ ] Path traversal prevented (file uploads)?
- [ ] SQL injection N/A (no direct DB access)?

**Dependencies:**
```bash
pip-audit
safety check
```
- [ ] No known vulnerabilities?
- [ ] Dependencies from trusted sources?

### Secrets Management (0-10)

- [ ] No API keys in code?
- [ ] No tokens in logs?
- [ ] Config file permissions restricted (chmod 600)?

**Tasks:**
1. Check `auth.py` - how is `keyring` used?
2. Run `pip-audit` - any vulnerabilities?
3. Review file upload code - path validation?

**Score: __/20**

---

## FINAL EVALUATION REPORT

### Scoring Summary

| Dimension | Max Score | Actual Score | Notes |
|-----------|-----------|--------------|-------|
| 1. Architecture & Design | 30 | __ | |
| 2. RFC Compliance | 30 | __ | |
| 3. Code Quality | 30 | __ | |
| 4. Functional Completeness | 30 | __ | |
| 5. API Endpoint Accuracy | 10 | __ | |
| 6. Testing & Validation | 30 | __ | |
| 7. Documentation Quality | 30 | __ | |
| 8. User Experience | 30 | __ | |
| 9. Production Readiness | 30 | __ | |
| 10. Security Audit | 20 | __ | |
| **TOTAL** | **270** | **__** | |

**Overall Grade:** ___% (Score/270 × 100)

---

### Grading Scale

| Grade | Score Range | Assessment |
|-------|-------------|------------|
| A+ | 95-100% | Production-ready, exemplary implementation |
| A | 90-94% | Production-ready with minor refinements |
| B+ | 85-89% | Near production, needs moderate work |
| B | 80-84% | Alpha-ready, significant work remains |
| C | 70-79% | Prototype stage, major gaps |
| D | 60-69% | Early development, needs restructuring |
| F | <60% | Incomplete, fundamental issues |

---

## CRITICAL FINDINGS

### P0 (Blockers - Must Fix Before Alpha)
1. [List any critical issues that prevent basic functionality]
2. ...

### P1 (High Priority - Should Fix Before Beta)
1. [List important issues affecting user experience]
2. ...

### P2 (Medium Priority - Fix Before v1.0)
1. [List nice-to-haves for production release]
2. ...

---

## TOP 10 RECOMMENDATIONS

**Priority Order:**

1. **[Recommendation #1]**
   - Issue: [Description]
   - Impact: [User/Developer/Security]
   - Effort: [Low/Medium/High]
   - Suggested Fix: [Actionable steps]

2. **[Recommendation #2]**
   - ...

3. ...

---

## IMPLEMENTATION GAPS vs RFC

**Missing from RFC v1.2:**

- [ ] Feature: `chat continue --chat-id <ID>`
- [ ] Feature: `--system` prompt support
- [ ] Feature: Stdin pipe support
- [ ] Feature: `--history-file` loading
- [ ] Feature: `rag search` semantic search
- [ ] Feature: `admin stats` and `admin diagnostics`
- [ ] ...

**Estimated Effort to Complete RFC:** __ hours

---

## BENCHMARK COMPARISONS

**Compare Against:**
- [mitchty/open-webui-cli](https://github.com/mitchty/open-webui-cli) - Prior art
- [openai/openai-python](https://github.com/openai/openai-python) - Industry standard CLI patterns

**Strengths of this implementation:**
1. ...

**Weaknesses compared to alternatives:**
1. ...

---

## NEXT STEPS - PRIORITIZED ROADMAP

### Week 1: Critical Path
1. [ ] Fix any P0 blockers
2. [ ] Achieve >70% test coverage
3. [ ] Verify all API endpoints
4. [ ] Complete streaming implementation

### Week 2: Polish
1. [ ] Implement missing RFC features
2. [ ] Improve error messages
3. [ ] Add comprehensive examples to docs
4. [ ] Set up CI/CD

### Week 3: Beta Prep
1. [ ] Security audit fixes
2. [ ] Performance optimization
3. [ ] Cross-platform testing
4. [ ] Beta user testing

---

## EVALUATION METHODOLOGY

**How to Use This Prompt:**

1. **Clone the repository:**
   ```bash
   git clone https://github.com/dannystocker/openwebui-cli.git
   cd openwebui-cli
   pip install -e ".[dev]"
   ```

2. **Read the RFC:**
   ```bash
   cat docs/RFC.md
   ```

3. **Systematically evaluate each dimension:**
   - Read the relevant code files
   - Run the specified commands
   - Fill in the scoring tables
   - Document findings in each section

4. **Synthesize the report:**
   - Calculate total score
   - Identify top 10 issues
   - Prioritize recommendations
   - Provide actionable roadmap

5. **Format output:**
   - Use markdown tables for scores
   - Include code snippets for issues
   - Link to specific files/line numbers
   - Be specific and actionable

---

## OUTPUT FORMAT

**Provide your evaluation in this structure:**

```markdown
# OpenWebUI CLI - Code Evaluation Report
**Evaluator:** [Your Name/LLM Model]
**Date:** 2025-11-30
**Version Evaluated:** v0.1.0

## Executive Summary
[2-3 paragraph overview of overall assessment]

## Scoring Summary
[Table with scores for all 10 dimensions]

## Critical Findings
[P0, P1, P2 issues]

## Top 10 Recommendations
[Prioritized list with effort estimates]

## Detailed Analysis
[Section for each of the 10 dimensions with findings]

## Conclusion
[Final verdict and next steps]
```

---

**BEGIN EVALUATION NOW**

Systematically work through dimensions 1-10, documenting findings, assigning scores, and building the final report.
