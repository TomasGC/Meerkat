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
# Every Meerkat suite, one invocation, unit tier
cd ~/.claude && python -m pytest -q -m unit
```
