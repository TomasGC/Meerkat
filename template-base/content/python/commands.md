#### Code Build
```bash
python -m build
```

#### Code Test — CI-safe
```bash
python -m pytest tests/ -m "unit or integration_mock" -v
```

#### Code Test — by tier
```bash
python -m pytest tests/unit/ -v
python -m pytest tests/integration_mock/ -v
python -m pytest tests/integration_real/ -v
python -m pytest tests/e2e/ -v
```

#### Code Coverage
```bash
python -m pytest tests/ -m "unit or integration_mock" --cov=src --cov-report=term-missing
```

#### Code Lint
```bash
ruff check .
ruff format --check .
mypy src/
```

#### Scripts Test
```bash
# Every Meerkat suite, one invocation, unit tier
cd ~/.claude && python -m pytest -q -m unit
```
