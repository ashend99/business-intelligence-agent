# Social Analytics Aggregated Flow Plan

## 1. Objective

Build a single-request social analytics flow where the frontend sends one request per selected platform/account/date range, and the backend returns one aggregated payload containing all data needed by the dashboard widgets.

This plan is designed to:

- Reduce frontend waterfall requests
- Improve perceived performance and consistency
- Keep flexibility for dynamic date ranges and platform-specific metrics
- Add a safe path for scaling through lightweight caching and partial-failure handling

## 2. Why This Approach

The previous pattern (many frontend calls per widget) introduces cumulative latency and fragile UI states.

A backend aggregation model allows:

- One network roundtrip from browser to API
- Parallel upstream metric fetching on the server
- Centralized retries, timeouts, validation, and logging
- Stable payload contracts for frontend rendering

## 3. Target Request/Response Contract

### Request (single endpoint)

The frontend should call one endpoint, for example:

- `GET /api/social/overview`

Suggested query parameters:

- `platform`: `fb` or `ig`
- `account_id`: platform account/page identifier
- `since`: ISO date (YYYY-MM-DD)
- `until`: ISO date (YYYY-MM-DD)
- `period`: `day`, `week`, etc.
- `timezone`: IANA timezone string

### Response (sectioned payload)

Return a single JSON object split into independently renderable sections:

- `summary`
- `kpis`
- `charts`
- `audience`
- `posts`
- `meta`

`meta` should include:

- request normalization values
- per-section timing (optional but useful)
- cache hit/miss details
- partial error list

## 4. Configuration-First Metric Routing

Keep all route templates and metric names in platform config files to avoid hardcoded endpoint logic.

Current config files:

- `src/mcp/facebook/config.yaml`
- `src/mcp/instagram/config.yaml`

Recommended structure style:

- `routing`: paths for accounts, insights, posts, audience, etc.
- `metrics`: names, periods, defaults, and limits per section

Benefits:

- Easy updates when API routes/metrics change
- No code deploy required for simple route/metric adjustments
- Better cross-platform consistency

## 5. Backend Orchestration Layer

Create an orchestration service responsible for turning one frontend request into one aggregated payload.

Responsibilities:

1. Validate and normalize request parameters
2. Resolve platform-specific config
3. Dispatch metric fetches concurrently (server-side)
4. Merge results into sectioned response contract
5. Attach metadata, partial errors, and cache diagnostics

Concurrency model:

- Run independent metric calls in parallel
- Use timeouts per sub-call to prevent one slow metric blocking all

## 6. Caching Strategy (Recommended)

Even with one frontend request, caching is still necessary for scale and rate-limit safety.

### 6.1 Cache Key Design

Cache keys must include all dynamic dimensions that affect correctness:

- platform
- account_id
- metric group/version
- since
- until
- period
- timezone

### 6.2 TTL Guidance

- Accounts/profile: 5-15 minutes
- Recent KPI metrics: 1-3 minutes
- Historical ranges: 15-60 minutes

### 6.3 Two-Level Caching (Optional, scalable)

1. Bucket-level cache (per day/per metric)
2. Query-level cache (exact request)

This supports arbitrary date ranges while controlling recomputation.

## 7. Partial-Failure Behavior

Do not fail the entire response if one metric source fails.

Rules:

- Return successful sections as usual
- Add failed section entries to `meta.partial_errors`
- Frontend shows section-level fallback states

Outcome:

- Dashboard remains useful even during transient API issues

## 8. Frontend Rendering Model

Frontend should consume one response and render progressively by section.

UI flow:

1. Render shell + placeholders immediately
2. Render `summary` and key KPIs first
3. Render charts and secondary sections next
4. Show targeted fallback for sections listed in `partial_errors`

This keeps UX responsive while preserving a clean one-request contract.

## 9. Observability and Diagnostics

Add lightweight telemetry in the aggregated endpoint:

- total request duration
- per-section fetch duration
- cache hit/miss ratio
- upstream error count

Use this data to tune:

- TTL values
- slow sections
- timeout budgets

## 10. Testing Plan

### API Contract Tests

- Validate response shape for each platform
- Validate required fields in each section

### Parameter Validation Tests

- invalid dates
- `since > until`
- unsupported period/platform

### Partial-Failure Tests

- one section fails, others succeed
- `meta.partial_errors` correctly populated

### Cache Tests

- key uniqueness by dynamic params
- TTL expiry behavior
- stale vs fresh response behavior (if implemented)

## 11. Incremental Rollout Plan

### Phase 1

- Implement aggregated endpoint for Instagram first
- Keep existing widget-level routes intact

### Phase 2

- Add Facebook to same aggregated contract

### Phase 3

- Switch frontend page to use aggregated endpoint only

### Phase 4

- Decommission redundant old per-widget routes if no longer needed

## 12. Implementation Checklist

1. Define and freeze request/response contract for `/api/social/overview`
2. Extend config files for all required routes/metrics
3. Build orchestration service with concurrent sub-fetches
4. Implement partial-failure response behavior
5. Add cache key builder and TTL policy
6. Integrate endpoint in API layer
7. Update frontend to consume sectioned payload
8. Add tests for contract, errors, and cache
9. Add timing and cache diagnostics in `meta`
10. Roll out by platform with feature flag or staged switch

## 13. Risks and Mitigations

### Risk: Payload becomes too large

Mitigation:

- Return only sections required by current tab/view
- Add optional `sections=` query parameter in future

### Risk: Dynamic date ranges create high cache cardinality

Mitigation:

- Include full date params in keys
- Use short TTL query cache + optional bucket cache

### Risk: Upstream API rate limits

Mitigation:

- Cache, request coalescing, and retry/backoff
- Prefer batched range calls where supported

## 14. Definition of Done

This flow is complete when:

1. Frontend uses one request for the analytics view
2. Backend responds with a stable sectioned payload
3. Sections can fail independently without breaking full response
4. Cache is active with validated dynamic key behavior
5. Tests and diagnostics are in place for maintainability
