# Roadmap: PostHog Analytics Overhaul

## Milestones

- ✅ **v1.0 PostHog Analytics Overhaul** — Phases 1-4 (shipped 2026-03-06)
- 🚧 **v1.1 Analytics Refinement** — Phases 5-7 (in progress)

## Phases

<details>
<summary>✅ v1.0 PostHog Analytics Overhaul (Phases 1-4) — SHIPPED 2026-03-06</summary>

- [x] Phase 1: Foundation (4/4 plans) — completed 2026-03-02
- [x] Phase 2: Business Events (3/3 plans) — completed 2026-03-02
- [x] Phase 3: Client Cleanup (3/3 plans) — completed 2026-03-03
- [x] Phase 4: Activation and Dashboards (3/3 plans) — completed 2026-03-05

</details>

### 🚧 v1.1 Analytics Refinement (In Progress)

**Milestone Goal:** Refactor v1.0 analytics code to follow good design patterns and enable PostHog frontend health metrics.

- [ ] **Phase 5: Foundation** - AnalyticsContext, identify_user, and typed event methods
- [ ] **Phase 6: Migration** - Migrate all call sites to new patterns and update tests
- [ ] **Phase 7: Frontend Health** - Enable PostHog web vitals, error tracking, network recording, and build dashboard

## Phase Details

### Phase 5: Foundation
**Goal**: Analytics service has clean internal abstractions — context resolution, identity management, and typed event methods — ready for call sites to adopt
**Depends on**: Phase 4 (v1.0 complete)
**Requirements**: REFAC-01, REFAC-03, REFAC-05
**Success Criteria** (what must be TRUE):
  1. AnalyticsContext can be constructed from a user_id and resolves consent, org_id, and user object with error isolation (no exceptions leak)
  2. AnalyticsService exposes typed methods (track_user_signed_up, track_user_logged_in, track_conversation_created, etc.) that accept explicit parameters instead of raw property dicts
  3. Identity tracking (set_person_properties + group_identify) is consolidated into a single identify_user method on AnalyticsService
  4. All new abstractions pass existing unit tests (no regressions)
**Plans:** 2 plans
Plans:
- [ ] 05-01-PLAN.md — AnalyticsContext dataclass, resolve_context factory, and identify_user method
- [ ] 05-02-PLAN.md — Typed event methods on AnalyticsService (10 track_* methods)

### Phase 6: Migration
**Goal**: Every analytics call site in the codebase uses the new Foundation patterns — no inline user/consent lookup, no raw property dicts, no duplicated identity blocks
**Depends on**: Phase 5
**Requirements**: REFAC-02, REFAC-04, REFAC-06, REFAC-07
**Success Criteria** (what must be TRUE):
  1. All route handlers that track events construct an AnalyticsContext instead of doing inline user/consent/org resolution
  2. All route handlers call typed event methods (e.g., track_conversation_created) instead of building property dicts and calling generic track()
  3. auth.py and oauth_device.py both call identify_user instead of duplicating set_person_properties + group_identify blocks
  4. Unit tests cover the new AnalyticsContext, typed event methods, and identify_user patterns
**Plans:** 2 plans
Plans:
- [ ] 06-01-PLAN.md — Migrate auth.py and oauth_device.py to resolve_context, identify_user, and typed methods
- [ ] 06-02-PLAN.md — Migrate conversation_callback_utils.py, billing.py, onboarding.py, and orgs.py to typed methods

### Phase 7: Frontend Health
**Goal**: PostHog captures frontend performance and error data automatically, with a dashboard to monitor it
**Depends on**: Nothing (independent of Phase 5-6, but sequenced after for focus)
**Requirements**: HEALTH-01, HEALTH-02, HEALTH-03, HEALTH-04
**Success Criteria** (what must be TRUE):
  1. PostHog web vitals autocapture is enabled and FCP, LCP, INP, CLS metrics appear in PostHog
  2. Unhandled JavaScript errors and promise rejections are captured by PostHog error tracking
  3. Session replay includes network request/response recording
  4. A PostHog dashboard exists showing web vitals trends and error rate insights
**Plans:** 2 plans
Plans:
- [ ] 07-01-PLAN.md — Enable web vitals, error tracking, and network recording in PostHog config
- [ ] 07-02-PLAN.md — Create Frontend Health dashboard in PostHog with web vitals + error insights

## Progress

**Execution Order:**
Phases execute in numeric order: 5 → 6 → 7

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 4/4 | Complete | 2026-03-02 |
| 2. Business Events | v1.0 | 3/3 | Complete | 2026-03-02 |
| 3. Client Cleanup | v1.0 | 3/3 | Complete | 2026-03-03 |
| 4. Activation and Dashboards | v1.0 | 3/3 | Complete | 2026-03-05 |
| 5. Foundation | v1.1 | 0/2 | Planning complete | - |
| 6. Migration | v1.1 | 0/2 | Planning complete | - |
| 7. Frontend Health | v1.1 | 0/2 | Planning complete | - |
