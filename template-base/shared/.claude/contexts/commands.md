# Commands - [Project Name]

Commands for managing this project.

---

## Tests — CI-safe (no external services)
```bash
pytest tests/ -m "unit or integration_mock" -v
```

## Tests — by tier
```bash
pytest tests/unit/ -v
pytest tests/integration_mock/ -v
pytest tests/integration_real/ -v    # requires live services
pytest tests/e2e/ -v
```
