#### Code Build
```bash
python -m build
```

#### Code Test — CI-safe
```bash
python -m pytest tests/ -m "units or integration_mocks" -v
```

#### Code Test — by tier
```bash
python -m pytest tests/units/ -v
python -m pytest tests/integration-mocks/ -v
python -m pytest tests/integration-reals/ -v
python -m pytest tests/e2e/ -v
```

#### Code Coverage
```bash
python -m pytest tests/ -m "units or integration_mocks" --cov=src --cov-report=term-missing
```

#### Code Lint
```bash
ruff check .
ruff format --check .
mypy src/
```

#### Scripts Test
```bash
# Run from ~/.claude — separate invocations (namespace isolation)
pytest ~/.claude/agents/black-box-analyzer/tests -m units
pytest ~/.claude/scripts/tests ~/.claude/scripts/cli/tests -m units
```
