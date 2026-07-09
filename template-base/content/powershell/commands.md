#### Code Lint
```powershell
Invoke-ScriptAnalyzer -Path . -Recurse
```

#### Code Test
```powershell
Invoke-Pester tests/ -Output Detailed
```

#### Code Coverage
```powershell
Invoke-Pester tests/ -CodeCoverage src/**/*.ps1
```

#### Scripts Test
```bash
# Run from ~/.claude — separate invocations (namespace isolation)
pytest ~/.claude/agents/black-box-analyzer/tests -m units
pytest ~/.claude/scripts/tests ~/.claude/scripts/cli/tests -m units
```
