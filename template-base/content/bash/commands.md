#### Code Lint
```bash
shellcheck scripts/**/*.sh
shfmt -d scripts/
```

#### Code Test
```bash
bats tests/
```

#### Code Format
```bash
shfmt -w scripts/
```

#### Scripts Test
```bash
# Run from ~/.claude — separate invocations (namespace isolation)
pytest ~/.claude/agents/black-box-analyzer/tests -m units
pytest ~/.claude/scripts/tests ~/.claude/scripts/cli/tests -m units
```
