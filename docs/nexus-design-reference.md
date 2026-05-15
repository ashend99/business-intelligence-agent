# Nexus Design Reference

Source: `nexus/` folder (Claude-generated React/JSX design prototype).  
Purpose: Map the Nexus design onto the existing Streamlit app, page by page, component by component.  
Approach: Implement one page at a time. Do not touch the `nexus/` files — they are read-only reference.

---

## 1. Overall Architecture

### Nexus (React prototype)
```
nexus/
├── app.jsx           # Root: routing, Sidebar, TopBar, ContextPanel, CommandPalette, Toast
├── shell.jsx         # Sidebar, TopBar, ContextPanel components
├── ai-components.jsx # Shared AI primitives: AIInsight, KPI, Citations, AgentChip, AskAIButton, SectionHead
├── charts.jsx        # SVG chart primitives: LineArea, MultiLine, Bars, Spark, HBar, Donut
├── icons.jsx         # SVG icon set (Icons.*)
└── pages/
    ├── home.jsx      # Dashboard overview: briefing, KPIs, 2×2 preview grid, agent log
    ├── chatbot.jsx   # Full-height chat: persona pills, message thread, composer, context panel
    ├── analytics.jsx # Primary chart, stat cards, AI insight, data table
    ├── reports.jsx   # Report card grid, slide-in detail panel, AI suggestion
    ├── sales.jsx     # Kanban pipeline, forecast bar, AI risk strip
    ├── team.jsx      # Member grid, workload bars, task board
    └── social.jsx    # Mention feed, sentiment stats, platform breakdown
```

### Current Streamlit App
```
src/ui/
├── app.py            # Home page — tile grid (AI Agent, Documents)
└── pages/
    ├── Chat.py       # Chat page (maps to chatbot.jsx)
    └── Documents.py  # Document upload/index page (no Nexus equivalent, custom)
```

---

## 2. Global Shell

### Sidebar (`shell.jsx → Sidebar`)
| Element | Detail |
|---|---|
| Width | 220px expanded / 56px collapsed, animated |
| Logo area | 48px height, indigo rounded-square icon + workspace name + collapse button |
| Quick switch | `⌘K` search bar (opens CommandPalette) |
| Nav items | Icon + label; active state highlighted with `--indigo` accent |
| Badges | "Chatbot" gets a teal dot with count; "Social" gets a grey chip |
| Bottom | Settings item + user avatar row (initials, name, role, chevron) |
| Collapse | Toggle button (PinLeft icon) in header; icon-only mode when collapsed |

**Streamlit approach:** `st.sidebar` with `st.page_link` for nav items. Collapse is native Streamlit sidebar collapse. User avatar and settings are decorative for now.

### TopBar (`shell.jsx → TopBar`)
| Element | Detail |
|---|---|
| Height | 48px |
| Left | Page title (bold 14px) + breadcrumb subtitle (grey, `·` separator) |
| Centre | Global search/ask bar (360px max, opens CommandPalette on click) |
| Right | `AgentChip` (N agents running, pulsing dot) + Bell (notification dot) + Sparkle (AI panel toggle) |

**Streamlit approach:** Custom HTML/CSS in each page header. `st.columns` for left/centre/right layout. AgentChip is cosmetic for now.

### Accent / Theme
- Primary accent: `--indigo: #6C63FF` (user-configurable in Nexus tweaks)
- Secondary colours: `--teal`, `--amber`, `--coral`, `--text`, `--text-2`, `--text-3`, `--border`, `--bg`, `--bg-2`, `--panel`, `--panel-2`
- Streamlit approach: Set via `st.markdown` CSS injection. Map to nearest Streamlit theme variables.

### Context Panel (right slide-in, 320px)
- Shows AI traces/sources for the active page
- Not a priority for initial Streamlit implementation

### Command Palette (`⌘K`)
- Fuzzy search across pages + recent items
- Not a priority for initial Streamlit implementation

### Toast notifications
- Auto-cycling "Agent finished" messages in bottom-right
- Streamlit `st.toast()` can approximate this

---

## 3. Pages

### 3.1 Home (`pages/home.jsx`) → `src/ui/app.py`

**Current state:** Two clickable tiles (AI Agent, Documents).

**Nexus design elements to adopt:**
1. **Welcome header** — "Good morning, [Name]" + date + workspace. Action buttons: Today, All teams, New report.
2. **AI Daily Briefing** (`AIInsight` component) — highlighted text, citations drawer, action buttons.
3. **KPI row** (4 cards) — label, large number, delta badge (coloured), sparkline. Cards: Revenue today, Open tickets, Team tasks due, Social mentions.
4. **2×2 preview grid** — each quadrant is a clickable panel navigating to its page:
   - Top-left: Analytics mini (line chart, revenue headline)
   - Top-right: Sales pipeline mini (horizontal bars by stage)
   - Bottom-left: Team mini (4 member cards with capacity bars)
   - Bottom-right: Social mini (recent mention items)
5. **Agent activity log** (bottom) — list of `AgentActionItem` rows with icons, descriptions, timestamps.

**Priority order:** KPI row → 2×2 grid tiles → Welcome header → AI briefing → Agent log.

**Streamlit implementation notes:**
- KPI cards: `st.metric` or custom HTML `<div>` cards with sparklines (use `st.line_chart` inside `st.columns` or SVG via `st.markdown`).
- Sparklines: inject inline SVG or use `streamlit-extras` sparklines.
- 2×2 grid: `st.columns(2)` with `st.container()` styled as panels; each uses `st.page_link` or a button to navigate.
- Preview charts inside grid: `st.line_chart` (Analytics) and `st.progress`-style bars (Sales).

---

### 3.2 Chatbot (`pages/chatbot.jsx`) → `src/ui/pages/Chat.py`

**Current state:** Basic chat UI exists (LangGraph agent connected).

**Nexus design elements to adopt:**
1. **Persona pills** — Default / Sales / Support / Analyst tab row. Maps to different system prompts / business_key.
2. **Thread toolbar** — New thread, History, ⋯ menu.
3. **Message bubbles:**
   - User: right-aligned, `panel-2` background, rounded top-right corner flat.
   - AI: left-aligned, Sparkle icon avatar, persona chip, token count, teal left-border response bubble.
4. **Follow-up suggestions** — row of small buttons below each AI response.
5. **Citations drawer** — collapsible "Sources · N" button showing filename + relevance %.
6. **Thinking state** — pulsing dot + "Thinking…" + tool call display.
7. **Composer** — textarea + attach button + KB mention button + Send button (primary).

**Priority order:** Message bubbles + composer → Thinking state → Citations → Follow-ups → Persona pills → Thread toolbar.

**Streamlit implementation notes:**
- Persona pills → `st.segmented_control` or radio buttons styled as pills.
- Message thread → `st.chat_message` (built-in) — already likely used.
- Citations → `st.expander` inside each AI message.
- Follow-ups → `st.button` row rendered after AI message.
- Composer → `st.chat_input` (built-in).

---

### 3.3 Analytics (`pages/analytics.jsx`) → **new page** `src/ui/pages/Analytics.py`

**Not yet implemented. Future page.**

**Nexus design elements:**
1. Metric/range pill tabs (Revenue / Traffic / Conversions, 7d / 30d / 90d / YTD).
2. Main chart (line or bar, toggleable) — full-width, 280px tall.
3. 4 KPI stat cards (Avg session, Bounce rate, New customers, Refunds).
4. AI anomaly insight with citations.
5. Data table — "Top sources" with sparklines per row.

**Streamlit implementation notes:**
- `st.tabs` or `st.segmented_control` for metric/range selectors.
- `st.line_chart` / `st.bar_chart` for main chart.
- Data table: `st.dataframe` with `column_config.LineChartColumn` for sparklines (Streamlit ≥1.36).

---

### 3.4 Reports (`pages/reports.jsx`) → **new page** `src/ui/pages/Reports.py`

**Not yet implemented. Future page.**

**Nexus design elements:**
1. Filter tabs (All / Ready / Scheduled) + type dropdown.
2. AI suggested report strip (`AIInsight`).
3. 3-column card grid — each card: title, status chip (Ready/Generating/Scheduled), date, type, AI summary, View + PDF buttons.
4. Slide-in detail panel (right drawer) on card click.

**Streamlit implementation notes:**
- Cards: custom HTML `<div>` grid (3-col `st.columns`).
- Status chips: coloured `st.badge` or inline HTML spans.
- Detail panel: `st.dialog` (modal) or right-column expander.

---

### 3.5 Sales (`pages/sales.jsx`) → **new page** `src/ui/pages/Sales.py`

**Not yet implemented. Future page.**

**Nexus design elements:**
1. Weighted pipeline headline + progress bar + pacing label.
2. AI risk strip (deals at risk, action buttons).
3. Kanban board — 5 columns (Lead / Qualified / Proposal / Negotiation / Closed), each with deal cards showing company, value, owner avatar, age, next action.
4. Risk-flagged cards highlighted in coral.

**Streamlit implementation notes:**
- Kanban: `st.columns(5)` with styled card `<div>`s.
- Risk highlights: CSS class injection.
- Not a priority until core pages are done.

---

### 3.6 Team (`pages/team.jsx`) → **new page** `src/ui/pages/Team.py`

**Not yet implemented. Future page.**

**Nexus design elements:**
1. Member grid with avatar, name, role, capacity bar, workload colour coding.
2. Task board (Kanban-lite).

---

### 3.7 Social (`pages/social.jsx`) → **new page** `src/ui/pages/Social.py`

**Not yet implemented. Future page.**

**Nexus design elements:**
1. Sentiment score + platform breakdown.
2. Live mention feed with platform icons, sentiment chips, reply buttons.

---

## 4. Shared Components (AI Primitives)

From `ai-components.jsx`:

| Component | Description | Streamlit equivalent |
|---|---|---|
| `AIInsight` | Indigo-accented block: sparkle icon + title + body + citations + action buttons | Custom `st.markdown` HTML block |
| `KPI` | Label + large number + delta badge (coloured) + sparkline | `st.metric` + inline SVG sparkline |
| `Citations` | Collapsible "Sources · N" with filename + relevance % | `st.expander` |
| `AgentChip` | "N agents running" chip with pulsing dot | Cosmetic HTML badge |
| `AskAIButton` | Indigo-soft "Ask AI about X" button | `st.button` with custom CSS |
| `SectionHead` | Title + subtitle + optional right slot | `st.markdown` + `st.columns` |
| `AgentActionItem` | Icon + text + timestamp row | Custom HTML list item |

---

## 5. Chart Primitives

From `charts.jsx` — all SVG, no external chart lib:

| Component | Use |
|---|---|
| `LineArea` | Line + gradient fill (Analytics main chart, Home analytics mini) |
| `MultiLine` | Multiple series on one axis |
| `Bars` | Vertical bar chart |
| `Spark` | Tiny inline sparkline (KPI cards) |
| `HBar` | Horizontal progress bar (Sales pipeline, Team capacity) |
| `Donut` | Donut/pie (Social platform breakdown) |

**Streamlit alternatives:**
- `st.line_chart`, `st.bar_chart` for full charts.
- `st.progress` for `HBar`.
- `column_config.LineChartColumn` for inline sparklines in dataframes.
- For pixel-perfect sparklines in KPI cards: inject inline SVG via `st.markdown`.

---

## 6. Implementation Order

| Priority | Page / Feature | Effort |
|---|---|---|
| 1 | **Home** — KPI row (4 metric cards with delta) | Low |
| 2 | **Home** — 2×2 preview grid (clickable panels) | Medium |
| 3 | **Home** — Welcome header | Low |
| 4 | **Home** — Agent activity log | Low |
| 5 | **Chat** — AI message bubble redesign (teal border, avatar, token count) | Medium |
| 6 | **Chat** — Citations drawer (collapsible sources) | Low |
| 7 | **Chat** — Follow-up suggestion buttons | Low |
| 8 | **Shell** — Sidebar redesign (logo, user avatar, nav badges) | Medium |
| 9 | **Shell** — TopBar with search bar + AgentChip | Medium |
| 10 | **Analytics page** — new page | High |
| 11 | **Reports page** — new page | High |
| 12 | **Sales page** — new page | High |
| 13 | **Team / Social pages** | High |

---

## 7. CSS / Styling Notes

The Nexus prototype uses CSS custom properties. Key ones to replicate in Streamlit via `st.markdown`:

```css
--indigo: #6C63FF;
--indigo-soft: rgba(108,99,255,0.12);
--indigo-soft-2: rgba(108,99,255,0.22);
--teal: #00C9A7;
--teal-soft: rgba(0,201,167,0.12);
--amber: #F5A623;
--coral: #FF6B6B;
--text: #111;
--text-2: #444;
--text-3: #888;
--border: #e5e5e5;
--bg: #f9f9f9;
--bg-2: #f3f3f3;
--panel: #fff;
--panel-2: #f5f5f5;
--mono: 'JetBrains Mono', monospace;
```

Panel card pattern:
```css
.panel {
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--panel);
}
.panel.clickable:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  transform: translateY(-2px);
  transition: all 0.18s ease;
}
```

Chip/badge pattern:
```css
.chip { border-radius: 99px; padding: 2px 8px; font-size: 11px; font-weight: 600; }
.chip.indigo { background: var(--indigo-soft); color: var(--indigo); }
.chip.teal   { background: var(--teal-soft);   color: var(--teal);   }
.chip.amber  { background: rgba(245,166,35,0.12); color: var(--amber); }
.chip.coral  { background: rgba(255,107,107,0.12); color: var(--coral); }
.chip.dot::before { content:''; display:inline-block; width:5px; height:5px; border-radius:50%; background:currentColor; margin-right:5px; }
```

---

## 8. Files NOT to Modify
- Everything under `nexus/` — read-only design reference
- `src/ingestion/` — ingestion pipeline, don't break it
- `src/tests/` — test suite must stay green
