# Cold Start Prompt for AI Agent

Use this prompt to launch a fresh AI agent that rebuilds the Asset Management demo from scratch.

## Launch Command

```bash
# Create a clean working directory
mkdir -p /tmp/nocobase-rebuild && cd /tmp/nocobase-rebuild

# Launch independent Claude Code agent
claude -p "$(cat <<'PROMPT'
# Task: Build NocoBase Asset Management System

You are building a complete enterprise asset management system using NocoBase MCP tools.

## Step 1: Get the Code

Clone the repo and read the documentation:
```
git clone https://github.com/Albert-mah/nocobase-skills-test.git
cd nocobase-skills-test
```

Read README.md and CLAUDE.md first, then read examples/asset-management/README.md.

## Step 2: Check Environment

Verify NocoBase is running:
```
curl -s http://localhost:14000/api/app:getLang | head -c 50
```

If NocoBase is NOT running, follow the Docker setup in README.md to start it.

## Step 3: Install Dependencies

```
pip install requests psycopg2-binary
```

## Step 4: Run Full Pipeline

Execute the 8 scripts in examples/asset-management/ in order:
1. nb-am-setup.py --drop
2. nb-am-field-upgrade.py
3. nb-am-pages.py
4. nb-am-workflows.py
5. nb-am-events.py
6. nb-am-js-blocks.py
7. nb-am-ai-employees.py
8. nb-am-seed-data.py

## Step 5: Document Issues

Write all problems, errors, confusions, and suggestions to ./notes.md as you go.
Format:
- [ERROR] step X: error description
- [UNCLEAR] section: what was confusing
- [MISSING] what info was missing
- [OK] step X: success details
PROMPT
)" --dangerously-skip-permissions --output-format text
```

## What to Expect

The agent will:
1. Clone the repo and read documentation
2. Check/setup NocoBase environment
3. Install Python dependencies
4. Run 8 scripts to build: 23 tables, 20 pages, 13 workflows, 27 events, 21 JS columns, 4 AI employees, 102 test records
5. Document any issues encountered

## Typical Run Time

~5-10 minutes depending on model speed and API latency.

## Troubleshooting

If the agent gets stuck:
- Check NocoBase is running: `curl -s http://localhost:14000/api/app:getLang`
- Check DB connectivity: `psql postgresql://nocobase:nocobase@localhost:5435/nocobase -c "SELECT 1"`
- Ensure Python packages installed: `pip install requests psycopg2-binary`
