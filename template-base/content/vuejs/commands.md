#### Code Build
```bash
npm run build
```

#### Code Test
```bash
npm run test:unit
```

#### Code Coverage
```bash
npm run test:unit -- --coverage
```

#### Code Lint
```bash
npm run lint
npx vue-tsc --noEmit
```

#### Scripts Test
```bash
# Run from ~/.claude — separate invocations (namespace isolation)
pytest ~/.claude/agents/black-box-analyzer/tests -m units
pytest ~/.claude/scripts/tests ~/.claude/scripts/cli/tests -m units
```
