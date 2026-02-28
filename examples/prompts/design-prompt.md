# HTML Prototype Design Prompt

This prompt template generates rich HTML prototypes from business requirements.
The AI designs as a frontend developer — no low-code platform context.

## Usage

```bash
# Generate HTML prototypes for a business system
claude -p "$(cat design-prompt.md)

$(cat itsm-requirements.md)" --model sonnet --output-dir /tmp/itsm-design/
```

---

## Prompt (copy below this line)

You are a senior frontend designer. Design an HTML prototype for a business management system.

### Output Format

Create ONE self-contained HTML file per page. Each file:
- Uses Tailwind CSS (CDN) + inline styles
- Includes realistic Chinese sample data (5-10 rows per table)
- Is immediately viewable in a browser
- File naming: `01-page-name.html`, `02-page-name.html`, ...

Also create an `index.html` with links to all pages + a sidebar navigation preview.

### Design Standards

Think like you're building a real enterprise SaaS product. For each page:

**Dashboard / List Pages:**
- KPI cards at top with icons, counts, trend arrows or sparklines
- Filter/search bar with smart defaults
- Data table with:
  - Status columns as colored badges/tags (not plain text)
  - Money columns formatted as ¥X,XXX.XX with conditional coloring
  - Date columns with relative time ("2小时前") or countdown ("还剩3天", overdue in red)
  - Progress bars where percentages exist
  - Priority/level as colored dots or badges
  - Actions column with icon buttons
- Pagination

**Forms (Add/Edit):**
- Logical field grouping with section headers
- Required field indicators
- Smart defaults (current user, today's date)
- Auto-calculation indicators (e.g., "= 数量 × 单价")
- Conditional field visibility hints (e.g., grey placeholder: "选择类型后显示")
- Inline validation messages

**Detail Pages / Popups:**
- Header card with key info summary + status badge
- Tabbed content for related data
- Timeline/activity log where status changes are tracked
- Sub-tables for child records
- Stat cards for computed summaries

**Charts (where data supports it):**
- Pie charts for category distribution
- Bar charts for top-N rankings
- Line charts for trends over time
- Use simple SVG or describe the chart intent clearly

### What NOT to do
- Don't write backend code
- Don't worry about API integration
- Don't add login/auth pages
- Don't build a full SPA framework — just static HTML pages with sample data

### Deliverables

For each page, output:
1. The complete HTML file
2. A brief comment at the top: `<!-- UX INTENT: what this page is for, key interactions -->`

At the end, create a `design-notes.md` summarizing:
- Total pages designed
- Key UX patterns used (badges, charts, auto-calc, etc.)
- Which columns/fields have special rendering (not plain text)
- Which forms have auto-calculation or auto-fill logic
- Which pages have charts or visualizations
