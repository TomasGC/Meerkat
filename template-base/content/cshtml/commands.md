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
# Every Meerkat suite, one invocation, unit tier
cd ~/.claude && python -m pytest -q -m unit
```
