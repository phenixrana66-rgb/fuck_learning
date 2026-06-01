# Type Safety

> Data-shape discipline for a JavaScript frontend that talks to a schema-heavy Python backend.

---

## Current Reality

The frontend is JavaScript-only, but the backend uses explicit Pydantic schemas and stable response envelopes.

That means “type safety” in this repo currently comes from:

* stable backend schema ownership
* careful request/response shaping in `src/api/`
* conservative normalization in `src/utils/` and route views
* disciplined route-param handling in `src/router/index.js` and route containers

Do not write Trellis guidance that assumes TypeScript types already exist.

---

## Required Patterns

* Treat backend response shape as authoritative; update frontend consumers when backend schemas change.
* Normalize optional/nullable values close to the boundary, as seen in request wrappers and storage helpers.
* Convert route params and query values deliberately instead of assuming they already have the right type.
* When a new payload shape becomes complex, document it in backend schemas first and keep frontend access centralized.

---

## Practical Safety Techniques

Useful local techniques in this codebase:

* central request wrappers that enforce the response envelope
* helper functions that coerce missing storage values to safe defaults
* view-level computed values that guard against absent nested data
* focused backend tests that protect the payload contract even when frontend tests are light

If a frontend-only data shape grows large, consider adding JSDoc typedefs or a normalization helper before spreading assumptions across many views.

---

## Forbidden Patterns

* Do not duplicate the same payload-shape assumptions across many route files.
* Do not trust raw localStorage JSON blindly without fallback/default handling.
* Do not let route params or query tokens flow through the app without normalization.

---

## Review Checklist

* If a backend response changed, did every frontend consumer get updated?
* Are default values and empty states still safe?
* Is data-shape normalization happening near the API/storage boundary instead of deep in the render tree?

---

## Scenario: Student Chapter Pace Suggestion Payload

### 1. Scope / Trigger
- Trigger: chapter learning pages now consume backend-owned `paceSuggestion` payloads from section detail, QA completion, practice checkpoints, and skip actions.
- Why this needs code-spec depth: the contract is JavaScript-only on the client, so if shape handling drifts across views, chapter re-entry and same-session updates fork immediately.

### 2. Signatures
- Student API wrappers:
  - `getStudentSectionDetail(...)`
  - `markStudentPageRead(...)`
  - `checkpointStudentPractice(...)`
  - `skipStudentPace(...)`
- Chapter view:
  - `src/views/student/SlideLearning.vue`
- Reusable UI:
  - `src/components/student/StudentPaceSuggestionCard.vue`

### 3. Contracts
- Treat backend `paceSuggestion` as server-owned state; the frontend only renders and performs local dismissal.
- Expected payload shape:
  - `paceMode: "supplement" | "reinforce" | "continue"`
  - `reasonSummary: string`
  - `triggerSource: "qa" | "practice"`
  - `updatedAt: string`
  - `suggestedAction: string`
  - `suggestedBlockType: string`
  - `suggestedBlockPayload: object`
  - `allowSkip: boolean`
- Frontend normalization rules:
  - fallback detail must include `paceSuggestion: null`
  - QA done payload replaces local `detail.paceSuggestion` immediately
  - page-read refresh may clear `detail.paceSuggestion` when the backend marks the section complete

### 4. Validation & Error Matrix
- missing `paceSuggestion` -> render no pacing card
- `paceMode === "continue"` -> render no persistent card
- skip request failure -> keep the local dismissal optimistic for the current view, but do not mutate the backend-owned suggestion object
- missing `suggestedBlockPayload.targetPageNo` -> do not attempt a forced page jump

### 5. Good / Base / Bad Cases
- Good: section detail loads with an active reinforce suggestion, the card renders, and clicking apply jumps to the suggested page.
- Base: QA completion returns `paceSuggestion: null`; the existing card disappears without needing a full reload.
- Bad: multiple parts of the view derive their own pace state from `understandingLevel` or `masteryPercent` instead of using the server payload.

### 6. Tests Required
- Backend regression must cover the `paceSuggestion` payload contract, since frontend tests here are light.
- Frontend verification:
  - `npm.cmd run build`
  - chapter page still compiles with fallback detail, page-read refresh, and QA streaming updates

### 7. Wrong vs Correct
#### Wrong
```javascript
// Re-derive pacing mode locally from partial pieces of state.
const paceMode = detail.value.masteryPercent < 60 ? 'reinforce' : 'continue'
```

#### Correct
```javascript
// Render the backend-owned suggestion directly and keep fallback shape safe.
const visiblePaceSuggestion = computed(() => {
  const suggestion = detail.value.paceSuggestion
  if (!suggestion || suggestion.paceMode === 'continue') return null
  return suggestion
})
```
