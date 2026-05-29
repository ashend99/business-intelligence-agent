# Facebook Analytics Frontend <-> API Connection Map

Files analyzed:
- frontend/src/pages/Social.jsx
- src/api/main.py

## Route Builders in Frontend Page
- `buildOverviewUrl` -> `GET /api/social/overview`
- `buildInsightsBatchUrl` -> `GET /api/social/insights`
- `buildTopPostsWindowUrl` -> `GET /api/social/top-posts`
- `buildAllPostsUrl` -> `GET /api/social/posts-metrics`
- `buildAudienceDemographicsUrl` -> `GET /api/social/audience-demographics`
- `buildEngagementBreakdownUrl` -> `GET /api/social/engagement-breakdown`

## Controls / Shared Components
- Platform dropdown + Page/Profile dropdown data source:
  - `GET /api/social/overview` (uses `summary.accounts` and `summary.selected_account`)
- Connected / Not Connected badge:
  - Indirectly from `GET /api/social/overview` result (account list length)
- Time range widget (analytics tab):
  - Updates `since`/`until` params used by:
    - `GET /api/social/overview`
    - `GET /api/social/top-posts`
    - `GET /api/social/engagement-breakdown`

## Tab Mapping

### 1) Overview tab
- Snapshot metric cards (Followers, Following/Page Likes, Posts):
  - `GET /api/social/overview` (`kpis`, selected account fields)
- Snapshot second row:
  - For Instagram (`Reach/Views/Engagement/Eng. Rate (30d)`): `GET /api/social/insights`
  - Engaged Accounts value: `GET /api/social/overview` (`kpis.engaged_accounts`)
  - For Facebook (`Reach/Engagement/Eng. Rate (Window)`): `GET /api/social/overview`
- Performance Overview chart:
  - `GET /api/social/overview` (`charts.performance_overview`, `charts.reach_since`, `charts.reach_until`)
- Posts Breakdown card (IG only):
  - `GET /api/social/posts-metrics`
- Engagement Breakdown card (IG only):
  - `GET /api/social/engagement-breakdown`
- Audience cards (IG only):
  - Age Distribution -> `GET /api/social/audience-demographics`
  - Top Countries -> `GET /api/social/audience-demographics`
  - Gender Split -> `GET /api/social/audience-demographics`
  - Gender by Age Group -> `GET /api/social/audience-demographics`

### 2) Analytics tab
- KPI row (Reach, Views, Eng., Engaged Accounts, Eng. Rate, Follows & Unfollows, Profile Link Taps):
  - `GET /api/social/overview` (`kpis.*`)
- Engagement Breakdown donut:
  - `GET /api/social/engagement-breakdown`
- Top Performance Posts table:
  - `GET /api/social/top-posts`
- Engagement Metric Details table:
  - `GET /api/social/engagement-breakdown` (current + previous breakdown)
- Key Insights cards:
  - Static UI content (no API call)

### 3) Posts tab
- All Posts table:
  - `GET /api/social/posts-metrics`

## Routes in main.py not used by this frontend page
- `GET /api/social/facebook/pages`
- `GET /api/social/facebook/reach`
- `GET /api/social/instagram/accounts`
- `GET /api/social/get_all_posts`

## Platform behavior
- `fb` and `ig`: connected to API routes above.
- `tk`: UI exists, but this page does not call social API routes for TikTok (state is reset/empty).
