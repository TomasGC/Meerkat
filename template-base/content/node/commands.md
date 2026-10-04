#### Code Build
```bash
npm run build
```

#### Code Test
```bash
npm test
```

#### Code Coverage
```bash
npm run test -- --coverage
```

#### Code Lint
```bash
npm run lint
npx tsc --noEmit
```

#### Scripts Test
```bash
# Every Meerkat suite, one invocation, unit tier
cd ~/.claude && python -m pytest -q -m unit
```
