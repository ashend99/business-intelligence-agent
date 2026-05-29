# Social Tabs API + Frontend Call Draft

## Goal
One API call per tab so all tab cards/sections load together.
Keep smaller existing endpoints for internal reuse and future compatibility.

## Endpoint Set (Tab-level)
1. GET /api/social/overview
2. GET /api/social/analytics
3. GET /api/social/posts

## Shared Query Params (All 3)
- platform: fb | ig
- account_id: string
- since: YYYY-MM-DD
- until: YYYY-MM-DD
- timezone: IANA timezone (default UTC)
- refresh: true | false (optional)

## Tab-specific Query Params
- /api/social/overview
  - include_breakdowns: true | false (optional, default true)
  - include_audience: true | false (optional, default true for ig)

- /api/social/analytics
  - metrics: comma list (optional, default reach,views,engagement,engagement_rate,engaged_accounts,follows_and_unfollows,profile_links_taps)
  - top_posts_limit: number (default 10)
  - compare_previous: true | false (default true)

- /api/social/posts
  - scope: lifetime | window (default lifetime)
  - sort_by: engagement_total | reach | created_at (default engagement_total)
  - limit: number (optional)
  - page: number (optional)

## Common Response Envelope (Same for all tabs)
{
  "tab": "overview|analytics|posts",
  "meta": {
    "platform": "ig",
    "account_id": "...",
    "since": "YYYY-MM-DD",
    "until": "YYYY-MM-DD",
    "timezone": "Asia/Colombo",
    "generated_at": "ISO-8601"
  },
  "cards": {},
  "sections": {},
  "partial_errors": [
    {
      "part": "audience_demographics",
      "message": "...",
      "code": "UPSTREAM_TIMEOUT"
    }
  ]
}

Notes:
- partial_errors present only when any internal sub-call fails.
- API still returns HTTP 200 if at least one major tab section is available.
- return 4xx only for request validation errors.

## Overview Tab Payload Draft
cards:
- profile_snapshot:
  - followers
  - following_or_page_likes
  - posts
- insights_snapshot:
  - reach
  - views (ig)
  - engagement
  - engagement_rate
  - engaged_accounts (ig)

sections:
- performance_overview:
  - series[]
  - x_axis_labels[]
- posts_breakdown (ig)
- engagement_breakdown (ig/fb if available)
- audience_demographics (ig):
  - age
  - country
  - gender
  - age_gender

## Analytics Tab Payload Draft
cards:
- kpis_window:
  - reach
  - views (ig)
  - engagement
  - engagement_rate
  - engaged_accounts (ig)
  - follows_and_unfollows (ig)
  - profile_links_taps (ig)

sections:
- engagement_breakdown_window
- top_performance_posts_window
- engagement_metric_details_current_vs_previous
- key_insights_summary (optional; can be generated later)

## Posts Tab Payload Draft
cards:
- totals:
  - total_posts
  - total_engagement
  - avg_engagement_rate

sections:
- all_posts_table:
  - rows[] with post metrics
- posts_type_breakdown
- pagination (optional)

## Internal Function Design (API Layer)
Use reusable internal functions that mcp_server can call independently later.

Core orchestration:
- build_overview_tab_payload(ctx)
- build_analytics_tab_payload(ctx)
- build_posts_tab_payload(ctx)

Reusable data functions:
- get_accounts_context(ctx)
- get_insights(metrics, ctx)
- get_kpi_bundle(tab, ctx)
- get_performance_series(ctx)
- get_engagement_breakdown(ctx)
- get_audience_demographics(ctx)
- get_top_posts(ctx)
- get_posts_metrics(ctx)
- compute_previous_window(ctx)

Normalization/helper functions:
- normalize_metric_definitions(platform)
- normalize_date_window(since, until, timezone)
- build_partial_error(part, err)
- safe_call(part_name, fn) -> (data, partial_error)

## Keep Existing Endpoints (Recommended)
Keep current card-level endpoints for now:
- /api/social/insights
- /api/social/top-posts
- /api/social/posts-metrics
- /api/social/audience-demographics
- /api/social/engagement-breakdown

Recommendation:
- Mark them as internal/stable-for-now in docs.
- New frontend should call only 3 tab-level endpoints.
- Old endpoints remain available for mcp_server internal tools and testing.

## Frontend Call Draft (One call per tab)
State model:
- tabData: { overview: null, analytics: null, posts: null }
- tabLoading: { overview: false, analytics: false, posts: false }
- tabError: { overview: null, analytics: null, posts: null }

Call behavior:
1. On tab switch:
- if cached tabData exists for current params, render immediately.
- otherwise call that tab endpoint once and store result.

2. On platform/account/window change:
- invalidate all three tab caches.
- call only active tab endpoint immediately.
- optional prefetch next likely tab in background.

3. Rendering:
- cards + sections render from one response object.
- if partial_errors exists, show a small non-blocking warning banner.

4. Request examples:
- Overview:
  /api/social/overview?platform=ig&account_id=1784...&since=2026-05-01&until=2026-05-28&timezone=Asia/Colombo&include_breakdowns=true&include_audience=true
- Analytics:
  /api/social/analytics?platform=ig&account_id=1784...&since=2026-05-01&until=2026-05-28&timezone=Asia/Colombo&top_posts_limit=10&compare_previous=true
- Posts:
  /api/social/posts?platform=ig&account_id=1784...&since=2026-05-01&until=2026-05-28&timezone=Asia/Colombo&scope=lifetime&sort_by=engagement_total

## Clarification for Item #3 (Simple format)
Simple format means same top-level response shape for every tab:
- tab
- meta
- cards
- sections
- partial_errors

Only the inside content of cards/sections differs by tab.
This keeps frontend mapping easy and mcp_server wrappers predictable.

## Suggested Implementation Order
1. Freeze response contracts for 3 tab endpoints.
2. Build internal reusable functions first.
3. Wire 3 tab endpoints using safe_call and partial_errors.
4. Switch frontend calls to 3 tab endpoints.
5. Keep old endpoints as compatibility/internal APIs.
