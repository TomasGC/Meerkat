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
# Run from ~/.claude — separate invocations (namespace isolation)
pytest ~/.claude/agents/black-box-analyzer/tests -m units
pytest ~/.claude/scripts/tests ~/.claude/scripts/cli/tests -m units
```
