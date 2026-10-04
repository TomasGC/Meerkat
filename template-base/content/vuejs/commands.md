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
# Every Meerkat suite, one invocation, unit tier
cd ~/.claude && python -m pytest -q -m unit
```
