# Technical Search - Usage Examples

Complete guide for using the search-tech skill and its automation scripts.

---

## Quick Start

### Using the Skill (Recommended)

```bash
# In Claude Code
/search-tech "TypeScript async error handling" --tags typescript,async-await --sources stackoverflow,github
```

The skill handles:
- Query parsing and validation
- Parallel search execution across platforms
- Result aggregation and ranking
- Formatted output with source attribution

### Using Scripts Directly

```bash
cd ~/.claude/skills/search-tech/scripts

# Install dependencies
pip install -r requirements.txt

# Search StackOverflow
python search_stackoverflow.py "TypeScript async error handling" \
    --tags "typescript,async-await" \
    --min-score 10 \
    --output stackoverflow.json

# Search GitHub Issues
python search_github.py "TypeScript async error handling" \
    --language typescript \
    --output github.json

# Aggregate results
python aggregate_results.py stackoverflow.json github.json \
    --output final.json \
    --markdown results.md \
    --query "TypeScript async error handling"
```

---

## Examples

### Example 1: Basic Search

**Goal**: Find solutions for TypeScript async error handling

```bash
./example_basic.sh
```

**Output**:
- `final.json` - Top 10 results ranked by relevance
- `results.md` - Markdown report with source attribution

**Result structure**:
```json
{
  "success": true,
  "total_results": 10,
  "sources": {
    "stackoverflow": 6,
    "github_issue": 4
  },
  "results": [
    {
      "source": "stackoverflow",
      "result_type": "question",
      "title": "How to properly handle async errors in TypeScript?",
      "url": "https://stackoverflow.com/q/12345678",
      "score": 125,
      "rank_score": 187.5,
      "accepted": true,
      "tags": ["typescript", "async-await", "error-handling"],
      "excerpt": "When using async/await in TypeScript...",
      "created_date": "2025-01-15T10:30:00Z"
    }
  ]
}
```

### Example 2: Focused Search with Filters

**Goal**: Find recent, highly-voted React performance solutions

```bash
python scripts/search_stackoverflow.py "React performance optimization" \
    --tags "reactjs,performance" \
    --min-score 20 \
    --output react_perf.json

# View results
cat react_perf.json | jq '.results[] | {title, score, url}'
```

**Filters**:
- `--min-score 20` - Only results with ≥20 votes
- `--tags` - Narrow to React performance topics
- Implicit recency bonus in ranking

### Example 3: Language-Specific GitHub Search

**Goal**: Find Rust async runtime issues

```bash
python scripts/search_github.py "async runtime tokio" \
    --language rust \
    --output rust_async.json

# View top repositories
cat rust_async.json | jq '.results[] | {repository, title, score}'
```

**Output**:
```json
{
  "results": [
    {
      "source": "github_issue",
      "repository": "tokio-rs/tokio",
      "title": "Async runtime performance degradation in 1.x",
      "score": 45,
      "status": "closed"
    }
  ]
}
```

### Example 4: Parallel Multi-Source Search

**Goal**: Search all platforms simultaneously (fastest)

```bash
#!/usr/bin/env bash
set -euo pipefail

QUERY="memory leak detection Node.js"

# Run all searches in parallel
python scripts/search_stackoverflow.py "$QUERY" \
    --tags "node.js,memory-leaks" \
    --output /tmp/so.json &

python scripts/search_github.py "$QUERY" \
    --language javascript \
    --output /tmp/gh.json &

# Wait for all background jobs
wait

# Aggregate
python scripts/aggregate_results.py \
    /tmp/so.json /tmp/gh.json \
    --output /tmp/final.json \
    --markdown /tmp/results.md \
    --query "$QUERY"

cat /tmp/results.md
```

**Performance**: 3-5 seconds (vs 9-15 seconds sequential)

### Example 5: CI/CD Integration

**Goal**: Auto-search for build errors in CI pipeline

```yaml
# .gitlab-ci.yml
search_error_solutions:
  stage: debug
  script:
    - pip install -r ~/.claude/skills/search-tech/scripts/requirements.txt
    - |
      python ~/.claude/skills/search-tech/scripts/search_stackoverflow.py \
        "webpack build error $ERROR_MESSAGE" \
        --tags "webpack,build" \
        --min-score 10 \
        --output solutions.json
    - cat solutions.json | jq '.results[] | {title, url}' > error_solutions.txt
  artifacts:
    paths:
      - error_solutions.txt
  when: on_failure
```

---

## Output Formats

### JSON Schema

```json
{
  "success": boolean,
  "total_results": integer,
  "sources": {
    "stackoverflow": integer,
    "github_issue": integer,
    "github_discussion": integer
  },
  "results": [
    {
      "source": "stackoverflow" | "github_issue" | "github_discussion",
      "result_type": "question" | "issue" | "discussion",
      "title": string,
      "url": string,
      "score": integer,
      "rank_score": float,
      "excerpt": string,
      "tags": [string],
      "accepted": boolean,
      "comments": integer,
      "answer_count": integer,
      "status": string | null,
      "repository": string | null,
      "created_date": string (ISO 8601) | null
    }
  ],
  "query": {
    "keywords": [string],
    "tags": [string],
    "min_score": integer,
    "language": string | null
  },
  "error": string | null,
  "rate_limit_exceeded": boolean,
  "search_time_seconds": float
}
```

### Markdown Format

```markdown
## 🔍 Technical Search Results for "TypeScript async error handling"

### Top Results (10 found)

#### 1. ⭐ 125 👍 | Stackoverflow | ✅ Accepted
**How to properly handle async errors in TypeScript?**
Tags: typescript, async-await, error-handling
Source: https://stackoverflow.com/q/12345678

> When using async/await in TypeScript, proper error handling requires...

#### 2. 🐙 45 👍 | Github Issue | Closed
**Async error handling in TypeScript compiler**
Repository: microsoft/TypeScript
Source: https://github.com/microsoft/TypeScript/issues/12345

> This issue discusses improvements to async error handling...

---
**Search completed across multiple platforms**
```

---

## Rate Limits

### StackOverflow API

**Without API key**:
- 300 requests per day per IP
- Quota resets at midnight UTC

**With free API key**:
- 10,000 requests per day
- Register at: https://stackapps.com/apps/oauth/register

**Setup**:
```bash
# Set environment variable
export STACKOVERFLOW_API_KEY="your_key_here"

# Or add to search command
python scripts/search_stackoverflow.py "query" --api-key "$STACKOVERFLOW_API_KEY"
```

### GitHub CLI

**Requirements**:
- gh CLI installed and authenticated
- `gh auth login` (one-time setup)

**Rate limits**:
- 5,000 requests per hour (authenticated)
- Enforced by GitHub API

---

## Troubleshooting

### Error: "requests module not found"

```bash
# Install dependencies
cd ~/.claude/skills/search-tech/scripts
pip install -r requirements.txt
```

### Error: "gh command not found"

```bash
# Install GitHub CLI
# macOS
brew install gh

# Windows
winget install --id GitHub.cli

# Linux
sudo apt install gh

# Authenticate
gh auth login
```

### Error: "Rate limit exceeded (StackOverflow)"

**Symptom**:
```json
{
  "success": false,
  "error": "StackOverflow rate limit exceeded (300/day)",
  "rate_limit_exceeded": true
}
```

**Solutions**:
1. Wait until midnight UTC for quota reset
2. Register for free API key (10,000 requests/day)
3. Use only GitHub search temporarily

### Error: "Search timeout (>10s)"

**Cause**: Slow network or API downtime

**Solutions**:
- Check internet connection
- Retry after a few minutes
- Check platform status pages:
  - StackOverflow: https://stackstatus.net/
  - GitHub: https://www.githubstatus.com/

### No Results Found

**Checklist**:
- ✅ Check spelling of keywords
- ✅ Try broader search terms
- ✅ Remove restrictive filters (--min-score, --tags)
- ✅ Try different platforms (one may have more relevant content)

---

## Advanced Usage

### Custom Ranking Weights

Modify `scripts/aggregate_results.py`:

```python
def calculate_rank_score(result: SearchResult) -> float:
    score = result.score
    
    # Adjust bonuses
    if result.accepted:
        score += 100  # Increase accepted answer bonus (default: 50)
    
    if result.created_date:
        days_old = (datetime.now() - result.created_date.replace(tzinfo=None)).days
        if days_old < 90:  # Prefer more recent (default: 180)
            recency_bonus = (90 - days_old) / 5  # Stronger recency (default: /10)
            score += recency_bonus
    
    engagement = result.comments + result.answer_count
    score += engagement * 5  # Higher engagement weight (default: *2)
    
    return round(score, 2)
```

### Filter by Date Range

```bash
# StackOverflow: Last 6 months
python scripts/search_stackoverflow.py "query" \
    --from-date "2025-10-01" \
    --to-date "2026-03-31"
```

### Export to Different Formats

```bash
# CSV
cat final.json | jq -r '.results[] | [.title, .url, .score] | @csv' > results.csv

# HTML
cat final.json | jq -r '.results[] | "<li><a href=\"\(.url)\">\(.title)</a> (\(.score) votes)</li>"' > results.html

# Plain text
cat final.json | jq -r '.results[] | "\(.title)\n\(.url)\n"' > results.txt
```

---

## Integration Examples

### VS Code Extension

```typescript
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function searchTechnicalSolution(query: string): Promise<SearchResult[]> {
    const scriptPath = '~/.claude/skills/search-tech/scripts';
    
    // Parallel execution
    const [soResult, ghResult] = await Promise.all([
        execAsync(`python ${scriptPath}/search_stackoverflow.py "${query}" --output /tmp/so.json`),
        execAsync(`python ${scriptPath}/search_github.py "${query}" --output /tmp/gh.json`)
    ]);
    
    // Aggregate
    await execAsync(`python ${scriptPath}/aggregate_results.py /tmp/so.json /tmp/gh.json --output /tmp/final.json`);
    
    const results = JSON.parse(fs.readFileSync('/tmp/final.json', 'utf8'));
    return results.results;
}
```

### Slack Bot

```python
from slack_bolt import App
import subprocess
import json

app = App(token="xoxb-your-token")

@app.command("/search-tech")
def handle_search(ack, command, say):
    ack()
    query = command['text']
    
    # Run search
    subprocess.run([
        'python', 'scripts/search_stackoverflow.py', query,
        '--output', '/tmp/so.json'
    ])
    subprocess.run([
        'python', 'scripts/search_github.py', query,
        '--output', '/tmp/gh.json'
    ])
    subprocess.run([
        'python', 'scripts/aggregate_results.py',
        '/tmp/so.json', '/tmp/gh.json',
        '--output', '/tmp/final.json'
    ])
    
    # Parse results
    with open('/tmp/final.json') as f:
        data = json.load(f)
    
    # Format for Slack
    blocks = []
    for result in data['results'][:5]:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{result['title']}*\n{result['url']} ({result['score']} votes)"
            }
        })
    
    say(blocks=blocks)
```

---

## Performance Tips

1. **Use parallel execution** - 3-5x faster than sequential
2. **Set appropriate timeouts** - Default 10s per platform
3. **Cache results** - Store in `/tmp/` for repeated queries
4. **Limit result count** - Top 10 is usually sufficient
5. **Use specific tags** - Narrow search scope reduces API load

---

## Dependencies

**Required**:
- Python 3.12+
- `requests>=2.31.0` (StackOverflow API)

**Optional**:
- `gh` CLI (GitHub search)
- StackOverflow API key (higher rate limits)

**Install**:
```bash
cd ~/.claude/skills/search-tech/scripts
pip install -r requirements.txt
```

---

## Testing

```bash
# Run example
cd ~/.claude/skills/search-tech/examples
./example_basic.sh

# Check output
ls -lh /tmp/*.json /tmp/*.md

# Validate JSON
cat /tmp/final.json | jq '.'

# View markdown
cat /tmp/results.md
```

---

## Support

**Issues**:
- Skill behavior: Check SKILL.md operational guidelines
- Script errors: Check script comments and docstrings
- API issues: Check platform status pages

**Debugging**:
```bash
# Enable verbose output
python scripts/search_stackoverflow.py "query" --verbose

# Check HTTP responses
python scripts/search_stackoverflow.py "query" --debug
```
