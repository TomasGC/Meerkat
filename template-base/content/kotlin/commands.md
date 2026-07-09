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
# Run from ~/.claude — separate invocations (namespace isolation)
pytest ~/.claude/agents/black-box-analyzer/tests -m units
pytest ~/.claude/scripts/tests ~/.claude/scripts/cli/tests -m units
```
