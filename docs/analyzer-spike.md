# Free Analyzer Spike (#67)

> **TL;DR**: 16 free, open-source tools were run on `fixtures/projects/` and compared with the seeded issues in
> `fixtures/golden/*/expected/`. Fourteen are kept as inputs of the adapters issue (#68), two are dropped. No tool
> covers SQL beyond regex, and every tool that needs a runnable project (coverage) cannot use the fixtures as shipped.

---

## Method

- Run on 2026-10-24, Windows 11, Git Bash, Python 3.12.10, Go 1.25.6, .NET SDK 10.0.401, 31.5 GB RAM, no local model.
- Fixtures: `python_project`, `go_project`, `kotlin_project`, `sql_project`: six small files. Results show whether a tool
  catches each seeded pattern, not its precision on a real code base.
- Licences read from each tool's repository with `gh api repos/<owner>/<repo>`; `NOASSERTION` resolved from the licence file.
- Native installs only. Docker was set aside: Docker Desktop is not open source, and its VM competes with the local model for RAM.

---

## Results

| Tool | Version | Licence | Agent | Catches (seeded records) | False positives / noise | Install and run cost | Verdict |
|------|---------|---------|-------|--------------------------|-------------------------|----------------------|---------|
| Opengrep | 1.32.0 | LGPL-2.1 | SSA | Own 4 rules: 4 of 4 on their lines (sleep, unclosed file, Go type assertion, Kotlin MD5), all missed by the other tools; SQL in `generic` mode: 6 of 12 SQL records | None on the own rules | 51 MB exe, native Windows, 3 s (7 s generic); rule ids come out prefixed with the rules path | Keep, run as a CLI process (LGPL) |
| Bandit | 1.9.4 | Apache-2.0 | SSA | Python: 6 of 13 code records (hardcoded secret, MD5, pickle, SQL string, eval, swallowed exception) | `import pickle` (B403) next to the pickle load (B301) | Already installed, <1 s | Keep |
| gosec | 2.30.0 | Apache-2.0 | SSA | Go: 4 of 5 (secret, MD5 twice, command injection) | MD5 reported twice (G401 + G501); unchecked assertion missed because the fixture does not compile | 103 MB exe, needs Go 1.26 (auto-downloaded toolchain), 4 s | Keep |
| detekt | 1.23.8 | Apache-2.0 | SSA | Kotlin: 1 of 4 (empty catch) | TODO comment, unused property: not seeded | 66 MB jar, needs a JDK, 1.3 s | Keep, low yield |
| Trivy | 0.76.1 | Apache-2.0 | SSA | `deploy.yaml`: 3 of 3 (host namespace, privileged, hostPort) | 16 LOW hardening items beyond the golden file | 171 MB exe + **1.6 GB** vulnerability DB on first run, 9 s | Keep (misconfig, secrets) |
| Gitleaks | 8.30.1 | MIT | SSA | 0: the fixtures hold placeholders by design | None | 22 MB, module path pinned to the old name | Keep |
| OSV-Scanner | 2.7.0 | Apache-2.0 | SSA | No manifest in the fixtures; synthetic requirements.txt: 44 advisories over 5 packages, transitive included | None | 83 MB, needs Go 1.27, 1.7 s, needs network | Keep |
| pip-audit | 2.10.1 | Apache-2.0 | SSA | Same synthetic file: 14 advisories, direct packages only | None | Already installed, 63 s | Drop: OSV-Scanner is 36x faster and transitive |
| ast-grep | 0.42.3 | MIT | SSA, CCA | 4 of 5 inline patterns on their lines, in 0.07-0.24 s | Cannot express "not inside" on the CLI | Already installed | Keep, fast second matcher |
| jscpd | 5.4.2 | MIT | CCA | DRY pair (service.py 9 and 17): 0 at defaults, found with `--min-lines 3 --min-tokens 20` | None | 43 MB, npm, 0.5 s | Keep, with tuned thresholds |
| lizard | 1.24.3 | MIT | CCA | KISS (`kitchen_sink`, CCN 6): 0 at the default CCN 15, found with `-C 4` | None | Under 1 MB, pip | Keep, threshold configured |
| vulture | 2.16 | MIT | CCA | Python YAGNI: all 12 unused-function records | `PASSWORD`, `DEBUG`, `login` flagged, not in the golden file | Already a repo lint tool | Keep |
| ruff | 0.16.10 | MIT | CCA | Default rules: 8 findings (blind except, undefined name, `try/except/pass`); `--select ALL`: 63, mostly docstring and annotation style | Style noise at `--select ALL` | Already installed | Drop: Python only, adds nothing over Bandit and vulture |
| coverage.py | 7.13.5 | Apache-2.0 | BBA | Per-line and per-branch data (29% on three throwaway tests; lines 83-84 flagged untested) | None | Already installed; needs `--source` | Keep |
| `go test -cover` | Go 1.25.6 | BSD-3-Clause (Go) | BBA | Per-block profile (1 of 6 blocks) | None | Built in; needs `go.mod` and a compiling package | Keep |
| coverlet | 6.x | MIT | BBA | Line coverage in Cobertura XML (Calc 50%) | Test class and generated `Program` listed as code | NuGet restore 1.5 min (three feeds); test assembly excluded by default, needs `IncludeTestAssembly` | Keep |

Seeded-record coverage by language (best combination of kept tools):
Python 8 of 13 code records (Bandit 6 + Opengrep 2), Go 5 of 5 (gosec 4 + Opengrep or ast-grep 1), Kotlin 2 of 4
(detekt 1 + Opengrep 1), `deploy.yaml` 3 of 3 (Trivy), SQL 6 of 12 (Opengrep generic, regex only).

---

## Not used

| Tool | Why |
|------|-----|
| CodeQL | Paid for private repositories |
| Semgrep registry rules | Semgrep Rules License v1.0, not open source (checked in `semgrep/semgrep-rules`); Opengrep with our own rules replaces it |
| TruffleHog | AGPL-3.0 |
| radon | No release since 2024 |
| JaCoCo | EPL-2.0 (weak copyleft), and coverlet already covers the BBA case; not measured |
| Mutation tools (mutmut, Stryker.NET, PIT) | Out of the spike's tool list; deferred |
| sqlfluff | MIT, the one candidate for SQL; not tried |

---

## What #68 needs to know

- **Tools are not on `PATH`.** `~/go/bin` is absent from Git Bash, detekt needs a JDK path, Trivy and Opengrep are bare executables.
  Adapters detect a tool by configured path first, then `PATH`, and say so when it is missing.
- **Output needs normalising.** Backslash paths, Opengrep rule ids prefixed with the rules file path, one defect reported by two
  gosec rules, coverlet listing test classes.
- **Coverage tools need a runnable project.** The fixtures have no `go.mod`, no manifests, and `Order` is undefined in `service.go`,
  so the BBA coverage adapters test against throwaway projects, not the golden fixtures.
- **Network.** OSV-Scanner and Trivy download data on first use; Trivy's cache is 1.6 GB. Go installs behind the company proxy
  fail unless `GOPROXY=https://proxy.golang.org,direct` is set for the command, and gosec and OSV-Scanner pull newer Go toolchains.
- **Thresholds are part of the tool.** jscpd and lizard report nothing at defaults.
- **SQL has no dedicated free tool here.** Regex rules in Opengrep match SSA's tables, so the SQL checkers keep their rules.

See `contexts/commands.md` once #68 lands for install steps and pinned versions.
