# Commands - [Project Name]

Commands for managing this project.

---

## Tests — CI-safe (no external services)
```bash
pytest tests/ -m "units or integration_mocks" -v
```

## Tests — by tier
```bash
pytest tests/units/ -v
pytest tests/integration-mocks/ -v
pytest tests/integration-reals/ -v    # requires live services
pytest tests/e2e/ -v
```
