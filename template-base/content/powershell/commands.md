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
# Every Meerkat suite, one invocation, unit tier
cd ~/.claude && python -m pytest -q -m unit
```
