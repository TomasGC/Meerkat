#### Code Build
```bash
go build ./...
```

#### Code Test
```bash
go test ./...
```

#### Code Coverage
```bash
go test ./... -coverprofile=coverage.out
go tool cover -html=coverage.out
```

#### Code Lint
```bash
golangci-lint run
```

#### Scripts Test
```bash
# Every Meerkat suite, one invocation, unit tier
cd ~/.claude && python -m pytest -q -m unit
```
