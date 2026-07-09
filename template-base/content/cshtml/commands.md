#### Code Build
```bash
dotnet build
```

#### Code Test
```bash
dotnet test
```

#### Code Coverage
```bash
dotnet test --collect:"XPlat Code Coverage"
```

#### Code Lint
```bash
dotnet format --verify-no-changes
```

#### Code Dev
```bash
dotnet watch run --project src/MyApp
```

#### Scripts Test
```bash
# Run from ~/.claude — separate invocations (namespace isolation)
pytest ~/.claude/agents/black-box-analyzer/tests -m units
pytest ~/.claude/scripts/tests ~/.claude/scripts/cli/tests -m units
```
