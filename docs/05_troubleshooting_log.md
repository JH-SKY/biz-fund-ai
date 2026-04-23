# 05 Troubleshooting Log

## Scope

- Target flow 1: `test login -> onboarding -> business number verification -> business registration -> dashboard entry`
- Target flow 2: `admin login -> admin dashboard entry`
- Check order:
  1. Frontend click and route flow
  2. Backend API response contract
  3. Database schema and persistence
  4. Frontend state hydration and redirect guards
  5. User-facing fallback UX

## Flow Summary

### Expected user flow

1. User opens `/login`
2. User uses test login
3. User is routed into onboarding or dashboard
4. User enters business basics
5. Business number is verified
6. Business is registered
7. Dashboard loads with the registered business

### Expected admin flow

1. Admin opens `/admin/login`
2. Admin enters ID and password
3. Admin login API returns a usable admin session payload
4. Admin token is saved to the admin auth store
5. Admin is redirected to `/admin/dashboard`
6. Dashboard renders without immediate contract errors

## Findings

### Finding 1: Login page could stay on loading UI

#### Symptom

- `/login` returned `200`
- Browser still showed the loading screen instead of the actual page

#### Cause

- Auth guard rendering depended on `hasHydrated`
- In some cases the client-side hydrated state was not being flipped reliably enough for the login route

#### Action taken

- Added a hydration bridge in providers so client boot always marks auth hydration complete
- Updated auth store so `login`, `logout`, and `setTokens` also force `hasHydrated: true`

#### Result

- Login route can move past the guard instead of being stuck on the spinner

### Finding 2: Test login API itself was stable

#### Reproduction

- Called `POST /api/v1/auth/test-login` with multiple test keys

#### Result

- Tested keys returned `200`
- Response contained usable auth payload data

#### Action taken

- Adjusted dev `test-login` behavior so it can return `is_new_user: false` for the direct-entry dev flow

#### Result

- Test login is suitable for quickly validating post-login routing

### Finding 3: Onboarding register was broken by DB schema mismatch

#### Symptom

- `POST /api/v1/onboarding/register` returned `500 Internal Server Error`

#### Cause

- Backend business registration code expected additional verification-related columns in `businesses`
- Local DB schema did not contain those columns

#### Missing columns found

- `is_biz_no_verified`
- `biz_verified_status`
- `tax_type`
- `biz_verified_at`

#### Action taken

- Verified actual schema through direct DB inspection
- Added the missing columns directly to the local development DB so the current code path could execute

#### Result

- Business registration completed successfully through the API

### Finding 4: Full Alembic upgrade is currently blocked

#### Symptom

- `alembic upgrade head` did not finish locally

#### Cause

- A migration requires PostgreSQL `pgvector`
- The local DB instance does not currently provide that extension

#### Result

- Local schema can be repaired for the onboarding flow
- Full migration consistency is still a remaining task

### Finding 5: Onboarding had no manual fallback when verification infrastructure failed

#### Symptom

- External business verification failure could hard-block onboarding progression

#### Cause

- Frontend treated verification infrastructure errors as terminal failures
- There was no fallback path for manual business registration

#### Action taken

- Added a manual registration continuation path for infrastructure-related verification errors
- Kept hard validation for truly invalid business numbers

#### Result

- Users can continue onboarding when the verification backend is temporarily unavailable

### Finding 6: Admin login succeeded visually but did not complete navigation

#### Symptom

- `/admin/login` showed a success toast after valid credentials
- User was not reliably entering the admin dashboard after login

#### Causes

- Frontend expected admin login response fields:
  - `admin_token`
  - `admin_id`
  - `name`
  - `role`
  - `expires_at`
- Backend was only returning:
  - `access_token`
  - `token_type`
- Admin auth store had no hydration guard, so protected routes could evaluate before persisted state restoration
- Admin dashboard stats payload shape did not match frontend expectations for `popular_policies`

#### Actions taken

- Updated admin login backend response contract to return the fields the frontend actually uses
- Added hydration tracking to the admin auth store
- Updated `AdminGuard` and `AdminPublicGuard` to wait for hydration before redirecting
- Fixed admin dashboard stats payload keys so dashboard rendering matches frontend expectations

#### Result

- Admin login now has a consistent token contract
- Admin redirect logic is less likely to bounce or stall on first render
- Admin dashboard first fetch is aligned with the frontend data shape

## Fixes Applied

### Frontend

- `frontend/src/stores/auth-store.ts`
  - Force `hasHydrated: true` during auth state mutations
- `frontend/src/providers/index.tsx`
  - Added hydration bridge to unblock login rendering
- `frontend/src/providers/QueryProvider.tsx`
  - Hid devtools behind an explicit env flag
- `frontend/src/features/onboarding/OnboardingForm.tsx`
  - Added manual registration fallback path
- `frontend/src/stores/admin-auth-store.ts`
  - Added hydration tracking for admin auth state
- `frontend/src/components/admin/AdminGuard.tsx`
  - Wait for hydration before redirect decisions

### Backend

- `backend/src/app/domains/auth/service.py`
  - Adjusted `test-login` dev flow behavior
- `backend/src/app/domains/admin/schema.py`
  - Updated admin login response schema to match frontend usage
- `backend/src/app/domains/admin/service.py`
  - Returned frontend-compatible admin login payload
  - Fixed dashboard stats payload shape

### Database

- Added missing business verification columns to local development DB for the onboarding flow

## Validation Log

### API and DB checks completed

- `POST /api/v1/auth/test-login` returned `200`
- `POST /api/v1/onboarding/verify-biz` returned a structured verification result
- `POST /api/v1/onboarding/register` succeeded after DB repair
- `GET /api/v1/businesses/me` returned `200` after registration

### Frontend checks completed

- Frontend `npm run type-check` passed after the current fixes

### Backend tests completed

- `backend/tests/domains/business/test_biz_verification.py`
  - `15 passed`

## Remaining Risks

- Full database migration still does not reach `head` because the local PostgreSQL instance does not currently provide the `pgvector` extension required by one migration
- Browser-level end-to-end verification for the full user flow is still pending in this environment
- Admin dashboard deeper pages were not fully audited yet
- BizMong chat flow has not yet been fully traced end-to-end

## Recommended Next Pass

1. Re-test admin login in the browser and confirm `/admin/dashboard` transition
2. Check admin dashboard first paint and failing widgets, if any
3. Verify normal user dashboard first entry after onboarding
4. Trace BizMong chat from input submit to assistant response
5. Stabilize local migration strategy around `pgvector`
