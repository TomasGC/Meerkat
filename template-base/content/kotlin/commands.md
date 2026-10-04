#### Code Build
```bash
./gradlew build
```

#### Code Test
```bash
./gradlew test
```

#### Code Coverage
```bash
./gradlew jacocoTestReport
```

#### Code Lint
```bash
./gradlew ktlintCheck
./gradlew detekt
```

#### Scripts Test
```bash
# Every Meerkat suite, one invocation, unit tier
cd ~/.claude && python -m pytest -q -m unit
```
