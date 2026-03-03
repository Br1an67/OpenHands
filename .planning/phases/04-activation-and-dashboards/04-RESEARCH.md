# Phase 4: Activation and Dashboards - Research

**Researched:** 2026-03-03
**Domain:** Server-side analytics instrumentation (activation events) + PostHog UI dashboard authoring
**Confidence:** HIGH for code instrumentation; MEDIUM for dashboard authoring (manual UI work, no API)

## Summary

Phase 4 splits into two distinct work streams: (1) server-side Python instrumentation for three activation events (ACTV-01, ACTV-02, ACTV-03), and (2) PostHog UI dashboard authoring for six dashboards (INST-03 through INST-08). The instrumentation work follows the exact same patterns established in Phases 1 and 2 — no new libraries, no new patterns. The dashboard work is manual PostHog UI configuration with zero code changes required.

ACTV-01 (`user activated`) requires detecting the user's first conversation reaching FINISHED state. The cleanest approach is to count the user's previous FINISHED conversations at the terminal-state hook point: if this is the first, fire `user activated`. The detection window covers both V1 (webhook_router.py after BIZZ-05 fires) and V0 (conversation_callback_utils.py). ACTV-02 (`git provider connected`) hooks into the V0 `store_provider_tokens` endpoint (`/api/add-git-providers`) in `openhands/server/routes/secrets.py`. This is a V0 file marked for deprecation April 2026, but it is the only current token storage path — the V1 equivalent is not yet built. ACTV-03 (`onboarding completed`) cannot be fully implemented: the onboarding form's backend endpoint (`useSubmitOnboarding`) is a TODO stub with no server-side persistence. The frontend calls `submitOnboarding({ selections })` which resolves immediately without hitting an API. A backend endpoint must be created before ACTV-03 can fire.

The six PostHog dashboards (INST-03 to INST-08) are pure PostHog UI work: create dashboards, add insights. All events and properties needed for these dashboards were already instrumented in Phases 1-3. No code changes are needed for dashboards. The planner should create one plan for backend event instrumentation (ACTV-01, ACTV-02) and one plan for creating the backend onboarding endpoint + ACTV-03 capture, and one plan (or task group) for PostHog UI dashboard authoring (INST-03 to INST-08).

**Primary recommendation:** Instrument ACTV-01 immediately after the existing BIZZ-05 `conversation finished` capture in both V1 webhook_router.py and V0 conversation_callback_utils.py, using a `StoredConversationMetadataSaas` count query to detect first-conversation. Hook ACTV-02 into the existing `store_provider_tokens()` endpoint with the same consent-guard pattern. Create a backend onboarding submission endpoint for ACTV-03. Build all six dashboards in PostHog UI as manual tasks — no code involved.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ACTV-01 | `user activated` captured server-side when user's first conversation reaches FINISHED state, with conversation_id, time_to_activate_seconds, llm_model, trigger | Hook point: right after existing BIZZ-05 `conversation finished` capture in `openhands/app_server/event_callback/webhook_router.py` (V1) and `enterprise/server/utils/conversation_callback_utils.py` (V0). First-conversation detection: count rows in `StoredConversationMetadataSaas` where `user_id = user_id AND conversation_id != current`. If count == 0, this is the first. `time_to_activate_seconds` = `(datetime.now() - user.accepted_tos).total_seconds()`. |
| ACTV-02 | `git provider connected` captured server-side on successful provider token storage with provider_type, org_id | Hook point: `openhands/server/routes/secrets.py` `store_provider_tokens()` after `await secrets_store.store(updated_secrets)`. Access to `provider_info.provider_tokens` gives provider_type list. user_id available via `get_user_id` dep or request state. Note: V0 legacy file — no user_id on request directly; needs `Depends(get_user_id)` added. |
| ACTV-03 | `onboarding completed` captured server-side with org group association, role, org_size, use_case | **BLOCKED**: `useSubmitOnboarding` is a TODO stub with no backend API endpoint. A new endpoint (`POST /api/onboarding` or equivalent enterprise route) must be created to receive role, org_size, and use_case selections and fire the analytics event. The onboarding form collects 3 steps: step1 = role (software_engineer, engineering_manager, etc.), step2 = org_size (solo, org_2_10, etc.), step3 = use_case (new_features, fixing_bugs, etc.). |
| INST-03 | Conversion funnel dashboard: signup → first conversation → finished → credit purchase | Manual PostHog UI. Four-step funnel using events: `user signed up`, `conversation created`, `conversation finished`, `credit purchased`. Steps ordered by event. No code. |
| INST-04 | Retention dashboard: conversation created as recurring engagement, grouped by signup cohort | Manual PostHog UI. Retention insight: start event = `user signed up` (first time), return event = `conversation created` (recurring). Grouped by weekly cohort. No code. |
| INST-05 | Credit usage dashboard: org-level credit purchased, credit limit reached, credit balance trends | Manual PostHog UI. Three insights grouped by org: trend of `credit purchased` broken down by org_id; trend of `credit limit reached` broken down by org_id; time series of credit_balance_after from `credit purchased` events. No code. |
| INST-06 | Churn signal dashboard: credit limit reached with no subsequent purchase within N days | Manual PostHog UI. HogQL query or funnel: users who had `credit limit reached` but did NOT have `credit purchased` within 14 days. Requires HogQL or multi-step funnel with exclusion. No code. |
| INST-07 | Usage pattern dashboard: events by model, trigger, agent_type; avg cost per conversation | Manual PostHog UI. Trend of `conversation finished` broken down by llm_model; breakdown by trigger; avg accumulated_cost_usd from conversation finished events. No code. |
| INST-08 | Product quality dashboard: success rate by terminal_state, error rates by model/trigger | Manual PostHog UI. Trend of `conversation finished` grouped by terminal_state property; trend of `conversation errored` grouped by llm_model; trend of `conversation errored` grouped by trigger. No code. |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| posthog (Python SDK) | ^7.0.0 | Event capture via `AnalyticsService.capture()` | Already integrated; Phase 1 established singleton pattern |
| SQLAlchemy (async) | project standard | Query `StoredConversationMetadataSaas` for first-conversation count | Used in all V1 database operations |
| FastAPI (Depends) | project standard | Inject `get_user_id` into the `store_provider_tokens` endpoint | Standard dependency injection pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| openhands.analytics.analytics_constants | project | `USER_ACTIVATED`, `GIT_PROVIDER_CONNECTED`, `ONBOARDING_COMPLETED` constants | All three are already defined in analytics_constants.py |
| enterprise.storage.user_store.UserStore | project | Fetch user object for consent flag and `accepted_tos` timestamp | Same as BIZZ-01/BIZZ-02 pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Count query on `StoredConversationMetadataSaas` for first-conversation | User-level `activated_at` flag column on User model | Flag column approach would require a migration and is cleaner but adds DB schema change; count query works with existing schema |
| Inline ACTV-01 after BIZZ-05 | Separate V1 callback | Inline is simpler; dedicated callback adds complexity for a single conditional event |

**Installation:** No new packages needed. All dependencies are already installed.

---

## Architecture Patterns

### Recommended Project Structure

No new files needed for ACTV-01 and ACTV-02. For ACTV-03:

```
enterprise/server/routes/
└── onboarding.py         # NEW: POST /api/onboarding endpoint
```

Files to modify:
```
openhands/app_server/event_callback/webhook_router.py         # ACTV-01 V1: after BIZZ-05 capture
enterprise/server/utils/conversation_callback_utils.py        # ACTV-01 V0: after BIZZ-05 capture
openhands/server/routes/secrets.py                            # ACTV-02: after store() call
```

### Pattern 1: Established Consent-Guard Pattern (copy verbatim from Phase 2)
**What:** Guard analytics calls with `if analytics:` and consent check, then capture.
**When to use:** Every analytics call in Phase 4. Same pattern as BIZZ-01 through BIZZ-06.
**Example:**
```python
# Source: enterprise/server/routes/auth.py lines 401-464 (established in Phase 1)
analytics = get_analytics_service()
if analytics:
    consented = user.user_consents_to_analytics is True  # None = undecided = not consented
    analytics.capture(
        distinct_id=user_id,
        event=analytics_constants.USER_ACTIVATED,
        properties={
            'conversation_id': conversation_id,
            'time_to_activate_seconds': time_to_activate_seconds,
            'llm_model': llm_model,
            'trigger': trigger,
        },
        org_id=org_id,
        consented=consented,
    )
```

### Pattern 2: First-Conversation Detection via Count Query
**What:** Count rows in `StoredConversationMetadataSaas` for the user before firing `user activated`.
**When to use:** ACTV-01 — only fires on the user's first finished conversation.
**Example:**
```python
# Source: enterprise/storage/stored_conversation_metadata_saas.py (table structure)
# Run this check after BIZZ-05 conversation finished fires:
from sqlalchemy import select, func
from storage.stored_conversation_metadata_saas import StoredConversationMetadataSaas

result = await db_session.execute(
    select(func.count()).where(
        StoredConversationMetadataSaas.user_id == user_uuid,
        StoredConversationMetadataSaas.conversation_id != str(conversation_id),
    )
)
prior_conversation_count = result.scalar() or 0
is_first_conversation = (prior_conversation_count == 0)

if is_first_conversation:
    # time_to_activate_seconds: from user.accepted_tos to now
    from datetime import datetime, timezone
    time_to_activate_seconds = None
    if user_obj.accepted_tos:
        now = datetime.now(timezone.utc)
        tos_ts = user_obj.accepted_tos
        if tos_ts.tzinfo is None:
            tos_ts = tos_ts.replace(tzinfo=timezone.utc)
        time_to_activate_seconds = (now - tos_ts).total_seconds()
    analytics.capture(
        distinct_id=user_id,
        event=analytics_constants.USER_ACTIVATED,
        properties={
            'conversation_id': str(conversation_id),
            'time_to_activate_seconds': time_to_activate_seconds,
            'llm_model': llm_model,
            'trigger': trigger,
        },
        org_id=org_id,
        consented=consented,
    )
```

### Pattern 3: ACTV-02 Git Provider Connected Hook
**What:** After tokens stored successfully, fire one event per new provider with a token.
**When to use:** ACTV-02 — only fire for providers that have a non-empty token (newly connected, not just host update).
**Example:**
```python
# Source: openhands/server/routes/secrets.py store_provider_tokens() ~line 148
# After: await secrets_store.store(updated_secrets)
# Need user_id — add Depends(get_user_id) to function signature

try:
    analytics = get_analytics_service()
    if analytics and user_id and provider_info.provider_tokens:
        from enterprise.storage.user_store import UserStore
        user_obj = await UserStore.get_user_by_id_async(user_id)
        if user_obj:
            consented = user_obj.user_consents_to_analytics is True
            org_id_str = str(user_obj.current_org_id) if user_obj.current_org_id else None
            for provider_type, token_value in provider_info.provider_tokens.items():
                if token_value.token:  # Only fire for providers with an actual token
                    analytics.capture(
                        distinct_id=user_id,
                        event=analytics_constants.GIT_PROVIDER_CONNECTED,
                        properties={
                            'provider_type': provider_type.value,
                        },
                        org_id=org_id_str,
                        consented=consented,
                    )
except Exception:
    logger.exception('analytics:git_provider_connected:failed')
```

### Pattern 4: ACTV-03 Backend Onboarding Endpoint
**What:** New FastAPI endpoint that receives onboarding form selections and fires `onboarding completed`.
**When to use:** ACTV-03 — must be created before this event can be tracked.
**Example:**
```python
# NEW: enterprise/server/routes/onboarding.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from openhands.analytics import analytics_constants, get_analytics_service
from openhands.server.user_auth import get_user_id

onboarding_router = APIRouter(prefix='/api')

class OnboardingSubmission(BaseModel):
    selections: dict[str, str]  # step_id -> option_id

@onboarding_router.post('/onboarding')
async def submit_onboarding(
    body: OnboardingSubmission,
    user_id: str = Depends(get_user_id),
):
    from enterprise.storage.user_store import UserStore
    user_obj = await UserStore.get_user_by_id_async(user_id)
    if user_obj:
        consented = user_obj.user_consents_to_analytics is True
        org_id_str = str(user_obj.current_org_id) if user_obj.current_org_id else None
        analytics = get_analytics_service()
        if analytics:
            analytics.capture(
                distinct_id=user_id,
                event=analytics_constants.ONBOARDING_COMPLETED,
                properties={
                    'role': body.selections.get('step1'),
                    'org_size': body.selections.get('step2'),
                    'use_case': body.selections.get('step3'),
                },
                org_id=org_id_str,
                consented=consented,
            )
            # Also associate with org group (SaaS-only, consent-gated inside service)
            analytics.group_identify(
                group_type='org',
                group_key=org_id_str or '',
                properties={
                    'onboarding_completed_at': datetime.now(timezone.utc).isoformat(),
                },
                distinct_id=user_id,
                consented=consented,
            )
    return {'status': 'ok', 'redirect_url': '/'}
```

**Frontend companion change** — update `useSubmitOnboarding` to POST to `/api/onboarding`:
```typescript
// Source: frontend/src/hooks/mutation/use-submit-onboarding.ts (current TODO stubs)
mutationFn: async ({ selections }: SubmitOnboardingArgs) => {
    const { data } = await openHands.post('/api/onboarding', { selections });
    return data;
},
```

### Pattern 5: PostHog Dashboard Authoring (UI-only, no code)
**What:** Manual PostHog UI steps to create dashboards with insights.
**When to use:** INST-03 through INST-08.
**Process:**
1. In PostHog, go to **Dashboards** → **New dashboard**
2. Name the dashboard, optionally pick a team/project
3. Click **Add insight** within the dashboard to create inline insights
4. For funnels: choose **Funnels**, add steps in order
5. For retention: choose **Retention**, set start event and return event, choose weekly cohort
6. For trends: choose **Trends**, select events, add breakdowns by property
7. For HogQL: choose **SQL**, write HogQL query
8. Save insight to dashboard

**Funnel configuration for INST-03 (conversion):**
- Step 1: `user signed up`
- Step 2: `conversation created`
- Step 3: `conversation finished`
- Step 4: `credit purchased`
- Conversion window: 30 days

**Retention configuration for INST-04:**
- Start event: `user signed up` (first time only)
- Return event: `conversation created`
- Cohort type: First time retention (weekly cohorts)

**Group breakdown for INST-05 (credit usage):**
- Use **Group analytics** breakdown by `org` group type
- Or breakdown by `org_id` event property (simpler, same data)

**Churn signal for INST-06 (HogQL):**
```sql
-- Users who hit credit limit but did NOT purchase within 14 days
SELECT
    person_id,
    min(timestamp) AS credit_limit_at
FROM events
WHERE event = 'credit limit reached'
  AND timestamp >= now() - interval 90 day
GROUP BY person_id
HAVING NOT EXISTS (
    SELECT 1 FROM events e2
    WHERE e2.event = 'credit purchased'
      AND e2.person_id = person_id
      AND e2.timestamp > credit_limit_at
      AND e2.timestamp < credit_limit_at + interval 14 day
)
```

### Anti-Patterns to Avoid
- **Firing `user activated` without checking first-conversation:** Without the count check, every finished conversation would fire `user activated`.
- **Firing ACTV-02 when only the host changes:** The `store_provider_tokens` endpoint updates both token and host. Only fire when `token_value.token` is non-empty — host-only updates should not produce a `git provider connected` event.
- **Counting conversations by checking the filesystem:** Use the database (`StoredConversationMetadataSaas`) not the file store — much faster and more reliable.
- **Firing `user activated` for STOPPED/AWAITING_USER_INPUT states:** The requirement says FINISHED state specifically. Only fire on non-error terminal states where the user's task completed. CONTEXT.md confirms STOPPED = `conversation finished` but `user activated` should use the same non-error terminal set.
- **Leaving `store_provider_tokens` without `user_id`:** The current function signature does not have `user_id` — it must be added via `Depends(get_user_id)` for the analytics call to work.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Consent enforcement | Custom consent check | `user.user_consents_to_analytics is True` | Already decided in Phase 1; must use `is True` not `==` |
| First-conversation detection | Custom user flag table | `StoredConversationMetadataSaas` count query | Existing table has exactly what's needed |
| PostHog funnel calculation | Custom SQL funnel | PostHog Funnels UI insight | PostHog handles window, ordering, attribution automatically |
| PostHog retention heatmap | Custom cohort SQL | PostHog Retention UI insight | Built-in first-time vs recurring distinction |
| Churn signal computation | Scheduled batch job | PostHog HogQL insight | Real-time, no infra required |
| Group breakdown by org | Custom org aggregation | PostHog group analytics (`org` group type, already configured in Phase 1) | `group_identify("org", org_id)` already fires on login |

**Key insight:** Dashboard work is 100% PostHog UI. Zero code changes needed for INST-03 through INST-08.

---

## Common Pitfalls

### Pitfall 1: `user activated` Firing on STOPPED or AWAITING_USER_INPUT
**What goes wrong:** The `_TERMINAL_FINISHED_STATES` set in `conversation_callback_utils.py` includes `STOPPED` and `AWAITING_USER_INPUT`. The existing BIZZ-05 capture fires for all of these. If ACTV-01 reuses that same trigger, it fires for STOPPED (user cancelled).
**Why it happens:** "First conversation reaches FINISHED state" means the AgentState.FINISHED enum value or ConversationExecutionStatus.FINISHED — not all non-error terminal states.
**How to avoid:** In V1, only fire ACTV-01 when `exec_status == ConversationExecutionStatus.FINISHED` (not STUCK, not ERROR). In V0, only fire when `event.agent_state == AgentState.FINISHED`.
**Warning signs:** `user activated` event count exceeds `conversation finished` (FINISHED) event count in PostHog.

### Pitfall 2: `user_id` Not on `store_provider_tokens` Request Context
**What goes wrong:** The current `store_provider_tokens()` signature is `(provider_info, secrets_store, provider_tokens)` — no `user_id`. Adding analytics requires knowing the user.
**Why it happens:** The OSS `secrets.py` route was designed to be user-context-agnostic (uses `SecretsStore` which resolves user from session internally).
**How to avoid:** Add `user_id: str | None = Depends(get_user_id)` to the function signature. In SaaS mode this will resolve to the authenticated user; in OSS mode it may return None, which is fine — wrap analytics in `if user_id:`.
**Warning signs:** `NameError: name 'user_id' is not defined` at runtime.

### Pitfall 3: Count Query Includes Current Conversation
**What goes wrong:** When checking if this is the first conversation, the current `conversation_id` may already exist in `StoredConversationMetadataSaas` by the time the terminal webhook fires.
**Why it happens:** `StoredConversationMetadataSaas` row is created at conversation start, before the conversation finishes.
**How to avoid:** Exclude the current `conversation_id` from the count: `StoredConversationMetadataSaas.conversation_id != str(conversation_id)`. The count of OTHER conversations == 0 means this is the first.
**Warning signs:** `user activated` never fires because count is always >= 1 (the current conversation is always counted).

### Pitfall 4: ACTV-03 Requires Non-Trivial Backend Work
**What goes wrong:** `useSubmitOnboarding.ts` is a stub — it does NOT POST to any endpoint. Implementing ACTV-03 requires: (1) create `enterprise/server/routes/onboarding.py`, (2) register the router in the enterprise server, (3) update the frontend hook to hit the real endpoint.
**Why it happens:** The onboarding form was built as a frontend-only feature with TODO backend stubs (visible in `use-submit-onboarding.ts` lines 14-16).
**How to avoid:** Plan ACTV-03 as a full-stack task: backend endpoint + frontend hook update + analytics capture. Do NOT assume the endpoint already exists.
**Warning signs:** `POST /api/onboarding` returns 404.

### Pitfall 5: Dashboard INST-06 (Churn) Requires HogQL, Not Standard Insight
**What goes wrong:** PostHog's standard funnel, retention, and trend insights cannot express "did NOT do X within N days of Y." This requires HogQL or the funnel exclusion step.
**Why it happens:** Standard PostHog insights optimize for positive event sequences. Negative conditions (did NOT purchase) require either HogQL or funnel exclusion steps.
**How to avoid:** Use a HogQL insight for INST-06 (see the SQL query in Code Examples). Alternatively use PostHog Funnels with an exclusion step — add `credit limit reached` as step 1 and `credit purchased` as exclusion within 14 days.
**Warning signs:** Standard trend or retention insight cannot capture the non-purchase cohort.

### Pitfall 6: ACTV-01 `time_to_activate_seconds` Timezone Mismatch
**What goes wrong:** `User.accepted_tos` is stored as `DateTime` without timezone in the DB (naive datetime). Subtracting a timezone-aware `datetime.now(timezone.utc)` raises `TypeError: can't subtract offset-naive and offset-aware datetimes`.
**Why it happens:** SQLAlchemy stores the value as stored — it depends on how `accepted_tos` was written. Some code paths use `datetime.now(UTC)` (aware), others use `datetime.now()` (naive).
**How to avoid:** Normalize before subtraction: if `user_obj.accepted_tos.tzinfo is None`, treat it as UTC via `.replace(tzinfo=timezone.utc)`.
**Warning signs:** `TypeError` in analytics capture; `time_to_activate_seconds` always `None`.

---

## Code Examples

Verified patterns from official codebase sources:

### ACTV-01 Integration Point (V1 webhook)
```python
# Source: openhands/app_server/event_callback/webhook_router.py — add after existing BIZZ-05 block (~line 296)
# The `user_obj`, `org_id`, `consented`, `conversation_id`, `exec_status` are all in scope from BIZZ-05

# ACTV-01: user activated (first finished conversation only)
if exec_status == ConversationExecutionStatus.FINISHED:
    try:
        from sqlalchemy import func, select
        from storage.stored_conversation_metadata_saas import StoredConversationMetadataSaas
        import uuid as _uuid

        user_uuid = _uuid.UUID(sandbox_info.created_by_user_id)
        prior_count_result = await db_session.execute(
            select(func.count()).where(
                StoredConversationMetadataSaas.user_id == user_uuid,
                StoredConversationMetadataSaas.conversation_id != str(conversation_id),
            )
        )
        prior_count = prior_count_result.scalar() or 0
        if prior_count == 0:
            from datetime import datetime, timezone
            time_to_activate_seconds = None
            if user_obj.accepted_tos:
                tos_ts = user_obj.accepted_tos
                if tos_ts.tzinfo is None:
                    tos_ts = tos_ts.replace(tzinfo=timezone.utc)
                time_to_activate_seconds = (datetime.now(timezone.utc) - tos_ts).total_seconds()
            analytics.capture(
                distinct_id=sandbox_info.created_by_user_id,
                event=analytics_constants.USER_ACTIVATED,
                properties={
                    'conversation_id': str(conversation_id),
                    'time_to_activate_seconds': time_to_activate_seconds,
                    'llm_model': app_conversation_info.llm_model,
                    'trigger': app_conversation_info.trigger.value if app_conversation_info.trigger else None,
                },
                org_id=org_id,
                consented=consented,
            )
    except Exception:
        _logger.exception('analytics:user_activated:failed')
```

### ACTV-01 Integration Point (V0 callback utils)
```python
# Source: enterprise/server/utils/conversation_callback_utils.py — add in the BIZZ-05 else branch (~line 121)
# After the existing CONVERSATION_FINISHED capture block
if event.agent_state == AgentState.FINISHED:
    try:
        from sqlalchemy import func, select
        from storage.stored_conversation_metadata_saas import StoredConversationMetadataSaas
        import uuid as _uuid
        with session_maker() as act_session:
            user_uuid = _uuid.UUID(user_id)
            prior_count = act_session.execute(
                select(func.count()).where(
                    StoredConversationMetadataSaas.user_id == user_uuid,
                    StoredConversationMetadataSaas.conversation_id != conversation_id,
                )
            ).scalar() or 0
        if prior_count == 0:
            from datetime import datetime, timezone
            time_to_activate_seconds = None
            if user_obj.accepted_tos:
                tos_ts = user_obj.accepted_tos
                if tos_ts.tzinfo is None:
                    tos_ts = tos_ts.replace(tzinfo=timezone.utc)
                time_to_activate_seconds = (datetime.now(timezone.utc) - tos_ts).total_seconds()
            analytics.capture(
                distinct_id=user_id,
                event=analytics_constants.USER_ACTIVATED,
                properties={
                    'conversation_id': conversation_id,
                    'time_to_activate_seconds': time_to_activate_seconds,
                    'llm_model': conv_meta.llm_model if conv_meta else None,
                    'trigger': None,  # V0: trigger not available in callback context
                },
                org_id=org_id_str,
                consented=consented,
            )
    except Exception:
        logger.exception('analytics:user_activated:v0:failed')
```

### `store_provider_tokens` Signature Addition
```python
# Source: openhands/server/routes/secrets.py line 109-113 (current signature)
# Before:
@app.post('/add-git-providers')
async def store_provider_tokens(
    provider_info: POSTProviderModel,
    secrets_store: SecretsStore = Depends(get_secrets_store),
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
) -> JSONResponse:

# After — add user_id dep:
@app.post('/add-git-providers')
async def store_provider_tokens(
    provider_info: POSTProviderModel,
    secrets_store: SecretsStore = Depends(get_secrets_store),
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    user_id: str | None = Depends(get_user_id),
) -> JSONResponse:
```

### PostHog HogQL Churn Signal (INST-06)
```sql
-- Source: PostHog docs — HogQL for negative conditions (verified via Context7)
-- Users who hit credit limit but did NOT purchase within 14 days
SELECT
    person_id,
    min(timestamp) AS credit_limit_at
FROM events
WHERE event = 'credit limit reached'
  AND timestamp >= now() - interval 90 day
GROUP BY person_id
HAVING NOT EXISTS (
    SELECT 1 FROM events e2
    WHERE e2.event = 'credit purchased'
      AND e2.person_id = person_id
      AND e2.timestamp > credit_limit_at
      AND e2.timestamp < credit_limit_at + interval 14 day
)
```

---

## Integration Points — Definitive Map

### ACTV-01: `user activated`
- **V1 File:** `openhands/app_server/event_callback/webhook_router.py`
- **V1 Hook:** After existing BIZZ-05 `conversation finished` capture, inside `exec_status == ConversationExecutionStatus.FINISHED` guard
- **V1 Context in scope:** `sandbox_info.created_by_user_id`, `conversation_id`, `app_conversation_info.llm_model`, `app_conversation_info.trigger`, `user_obj`, `org_id`, `consented`
- **V1 Note:** Requires `db_session` in scope — the V1 webhook already has async db access via injected dependencies
- **V0 File:** `enterprise/server/utils/conversation_callback_utils.py`
- **V0 Hook:** After existing CONVERSATION_FINISHED capture in `process_event()`, inside `event.agent_state == AgentState.FINISHED` guard
- **V0 Context in scope:** `user_id`, `user_obj`, `org_id_str`, `consented`, `conv_meta`, `conversation_id`
- **V0 Note:** Uses synchronous `session_maker()` (V0 pattern)

### ACTV-02: `git provider connected`
- **File:** `openhands/server/routes/secrets.py`
- **Function:** `store_provider_tokens()`, after `await secrets_store.store(updated_secrets)` (~line 148)
- **Change needed:** Add `user_id: str | None = Depends(get_user_id)` to function signature
- **Fire condition:** `if token_value.token:` — skip provider entries that are host-only updates
- **Available data:** `provider_info.provider_tokens` (dict of ProviderType → ProviderToken), `user_id`
- **V0 only:** No V1 equivalent endpoint exists yet

### ACTV-03: `onboarding completed`
- **New File:** `enterprise/server/routes/onboarding.py` (must be created)
- **Frontend file:** `frontend/src/hooks/mutation/use-submit-onboarding.ts` (must be updated to call real endpoint)
- **Onboarding data:** step1=role (software_engineer, engineering_manager, cto_founder, product_operations, student_hobbyist, other), step2=org_size (solo, org_2_10, org_11_50, org_51_200, org_200_1000, org_1000_plus), step3=use_case (new_features, app_from_scratch, fixing_bugs, refactoring, automating_tasks, not_sure)

### PostHog Dashboards (INST-03 to INST-08)
All dashboards are built in PostHog UI. No code changes. Events required are all already flowing:

| Dashboard | PostHog Insight Type | Events Used | Key Breakdown |
|-----------|---------------------|-------------|---------------|
| INST-03: Conversion Funnel | Funnels | user signed up → conversation created → conversation finished → credit purchased | None (linear funnel) |
| INST-04: Retention | Retention | Start: user signed up; Return: conversation created | Weekly cohort, first-time |
| INST-05: Credit Usage | Trends (3 insights) | credit purchased, credit limit reached | org_id property breakdown |
| INST-06: Churn Signal | HogQL or Funnel with exclusion | credit limit reached + NOT credit purchased | 14-day window |
| INST-07: Usage Patterns | Trends (3 insights) | conversation finished | llm_model, trigger, agent_type breakdowns |
| INST-08: Product Quality | Trends (2 insights) | conversation finished, conversation errored | terminal_state, llm_model, trigger |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Client-side `trackGitProviderConnected` in use-add-git-providers.ts | Server-side `git provider connected` via secrets.py | Phase 3 removed client; Phase 4 adds server | Clean migration — no double-counting |
| Client-side `trackOnboardingCompleted` in onboarding-form.tsx | Server-side `onboarding completed` via new endpoint | Phase 3 removed client; Phase 4 adds server | Requires new backend endpoint |
| Client-side activation tracking (none existed) | Server-side `user activated` via webhook terminal state | New in Phase 4 | More reliable than client-side (no ad-blockers) |
| No dashboards | Six dashboards in PostHog UI | Phase 4 new | Stakeholders can answer key questions without SQL |

**Deprecated/outdated:**
- `trackGitProviderConnected` in `use-add-git-providers.ts`: Already deleted in Phase 3; server-side replacement goes in Phase 4
- `trackOnboardingCompleted` in `onboarding-form.tsx`: Already deleted in Phase 3; server-side replacement requires new backend endpoint
- `useSubmitOnboarding` TODO stubs: Must be replaced with real API call in Phase 4

---

## Open Questions

1. **Does the V1 webhook have a `db_session` in scope for the count query?**
   - What we know: `webhook_router.py` uses FastAPI dependency injection. The existing BIZZ-05 code does `from enterprise.storage.user_store import UserStore` inline and calls `UserStore.get_user_by_id_async()`. The `StoredConversationMetadataSaas` count query needs a SQLAlchemy async session.
   - What's unclear: Whether the webhook handler already has an injected `AsyncSession` or whether a fresh `a_session_maker()` context manager must be used.
   - Recommendation: Inspect `webhook_router.py` injection state at implementation time. If no session is injected, use `async with a_session_maker() as session:` (same pattern as existing enterprise routes).

2. **Does ACTV-01 fire for STOPPED state?**
   - What we know: REQUIREMENTS.md says "user's first conversation reaches FINISHED state." CONTEXT.md (Phase 2) decided STOPPED fires as `conversation finished` not `conversation errored`.
   - What's unclear: Whether `user activated` should fire when a user's first conversation is STOPPED (user cancelled immediately), not actually FINISHED (agent completed task).
   - Recommendation: Be conservative — only fire `user activated` on `ConversationExecutionStatus.FINISHED` (V1) / `AgentState.FINISHED` (V0). A conversation the user immediately cancels is not a meaningful activation signal. The requirement wording "reaches FINISHED state" supports this interpretation.

3. **Where to register the new onboarding router in the enterprise server?**
   - What we know: Enterprise routes are registered in the enterprise server's router collection. Pattern established in `enterprise/server/routes/*.py`.
   - What's unclear: The exact file where routers are registered (e.g., `enterprise/app.py` or similar).
   - Recommendation: Grep for `billing_router` or `user_app_settings_router` import locations to find the router registration file.

4. **Should ACTV-02 fire on re-connections (token refresh)?**
   - What we know: `store_provider_tokens()` is called both for initial connection AND when a user updates their token (e.g., token expiry refresh). The existing logic checks if a provider is in `existing_providers` — if yes, it may be updating, not connecting fresh.
   - What's unclear: Whether re-storing an existing provider token should fire `git provider connected` again.
   - Recommendation: Fire only when the provider was NOT previously in `existing_providers` (i.e., `provider_type not in [p for p in user_secrets.provider_tokens]`). This fires on first connect, not on token refresh. Or accept some over-counting since PostHog funnels will count distinct users, not events.

---

## Validation Architecture

> `workflow.nyquist_validation` not present in `.planning/config.json` — section skipped.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase read: `openhands/analytics/analytics_constants.py` — `USER_ACTIVATED`, `GIT_PROVIDER_CONNECTED`, `ONBOARDING_COMPLETED` already defined
- Direct codebase read: `openhands/app_server/event_callback/webhook_router.py` lines 280-296 — existing BIZZ-05 V1 capture block (ACTV-01 V1 hook point)
- Direct codebase read: `enterprise/server/utils/conversation_callback_utils.py` lines 105-122 — existing BIZZ-05 V0 capture block (ACTV-01 V0 hook point)
- Direct codebase read: `openhands/server/routes/secrets.py` lines 109-158 — `store_provider_tokens()` full function (ACTV-02 hook point)
- Direct codebase read: `enterprise/storage/stored_conversation_metadata_saas.py` — table structure with `user_id`, `conversation_id`, `org_id` columns (first-conversation count query)
- Direct codebase read: `enterprise/storage/user.py` — `User.accepted_tos` (DateTime) for `time_to_activate_seconds`
- Direct codebase read: `frontend/src/hooks/mutation/use-submit-onboarding.ts` — confirmed stub with TODO comments (ACTV-03 blocked on backend)
- Direct codebase read: `frontend/src/routes/onboarding-form.tsx` — step1=role, step2=org_size, step3=use_case option IDs
- Direct codebase read: `openhands/analytics/analytics_service.py` — established consent-gate + capture pattern
- Context7 `/posthog/posthog.com` — PostHog funnel, retention, cohort, HogQL dashboard documentation
- Direct codebase read: `.planning/phases/02-business-events/02-RESEARCH.md` — established patterns confirmed working

### Secondary (MEDIUM confidence)
- Context7 PostHog docs — dashboard templates, HogQL syntax for negative conditions (INST-06)
- Pattern inference from Phase 2 implementation in `billing.py` and `auth.py` — consent-guard pattern consistency confirmed

### Tertiary (LOW confidence)
- None identified — all critical findings verified by direct code inspection

---

## Metadata

**Confidence breakdown:**
- ACTV-01 instrumentation: HIGH — hook points verified in both V1 and V0; first-conversation detection query confirmed against real schema
- ACTV-02 instrumentation: HIGH — hook point verified; user_id injection pattern standard
- ACTV-03 instrumentation: HIGH for approach; the backend stub is confirmed absent — requires creating new endpoint
- INST-03 to INST-08 dashboard authoring: MEDIUM — PostHog UI capabilities confirmed via Context7; actual dashboard steps are manual and not code-verifiable
- Pitfalls: HIGH — derived from direct code inspection of actual field types and existing patterns

**Research date:** 2026-03-03
**Valid until:** 2026-04-01 (V0 deprecation date; V0 ACTV-01 hook may become moot)
