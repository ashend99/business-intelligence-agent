# Overview Tab Frontend -> API Connection (Updated)

## Scope
This document covers only the Overview tab connection from frontend to API after the new config-driven changes.

## Frontend Entry
Source: frontend/src/pages/Social.jsx

Overview tab data is driven by one main request builder:
- buildOverviewUrl(extra)

Built query params:
- platform
- period
- since
- until
- timezone
- account_id (when page/profile selected)
- refresh=true (bootstrap/refresh calls)

Main fetch usage:
1. On platform change/bootstrap
- fetch(buildOverviewUrl({ refresh: 'true' }))

2. On selected account/page or time window change
- fetch(buildOverviewUrl({ account_id: selectedPage.id, refresh: 'true' }))

## API Route (Now Config-driven)
Source: src/api/main.py

Overview endpoint path is not hardcoded anymore.
It reads from config:
- social.overview.route

Current default route in config/config.yaml:
- /api/social/overview

Also config-driven defaults:
- social.overview.defaults.period
- social.overview.defaults.timezone

Supported periods are now read from:
- social.supported_periods

## API Builder
Source: src/api/social_overview.py

Frontend overview request is handled by:
- build_social_overview(...)

The builder now uses config/config.yaml for:
- behavior.enable_cache
- behavior.cache_ttl_seconds
- behavior.comparison_window
- defaults.chart_days
- defaults.top_posts_limit
- platform_rules.<platform>.include_sections
- platform_rules.<platform>.include_kpis

## Response Contract Used by Frontend (Overview Tab)
Frontend expects these top-level keys from overview API:
- summary
- kpis
- charts
- (optional for overview visuals) audience
- (optional for overview visuals) posts
- meta.partial_errors

Primary bindings in Overview tab UI:
1. Snapshot profile cards
- followers / following or page_likes / posts
- from summary.selected_account + kpis.posts_count

2. Snapshot insights row
- reach / views / engagement / engagement_rate / engaged_accounts
- from kpis + overviewInsights (insights endpoint still used for IG 30d snapshot)

3. Performance Overview chart
- charts.performance_overview
- charts.reach_since
- charts.reach_until

4. IG-only breakdown cards
- Posts Breakdown: derived from allPosts (posts metrics endpoint)
- Engagement Breakdown: engagement-breakdown endpoint
- Audience cards: audience-demographics endpoint

Note:
- Overview endpoint now supports section/KPI filtering by platform via config.
- Frontend still renders the defined Overview cards; missing sections should be avoided by config for active platform.

## New Connection Behavior Summary
- Frontend still makes one primary Overview API call for tab hydration.
- API route/defaults/period validation are config-driven.
- Overview payload assembly is config-controlled per platform (sections + KPI inclusion).
- Existing supporting endpoints remain available and still feed some IG overview visuals (insights/breakdowns/audience/posts metrics).
