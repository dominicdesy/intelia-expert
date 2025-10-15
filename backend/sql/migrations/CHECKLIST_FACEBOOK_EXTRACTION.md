# Checklist: Deploy Facebook Profile URL Extraction

## Quick Deployment Guide

Follow these steps in order to deploy the automatic Facebook profile URL extraction feature.

---

## Prerequisites

- [  ] Access to Supabase Dashboard
- [  ] Backend deployment access (DigitalOcean App Platform)
- [  ] Frontend deployment access

---

## Step 1: Database Migration

### 1.1 Add facebook_profile Column

- [  ] Go to https://supabase.com/dashboard
- [  ] Select project: **Intelia Expert**
- [  ] Go to **SQL Editor** (left sidebar)
- [  ] Click **New Query**
- [  ] Copy and paste: `backend/sql/migrations/add_facebook_profile_to_users.sql`
- [  ] Click **Run** (or Ctrl+Enter)
- [  ] Verify: "Success. No rows returned"

**Verification:**
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'facebook_profile';
```

Expected: `facebook_profile | text`

---

### 1.2 Update handle_new_user Trigger

- [  ] Same SQL Editor window
- [  ] Click **New Query**
- [  ] Copy and paste: `backend/sql/migrations/update_handle_new_user_facebook_extraction.sql`
- [  ] Click **Run**
- [  ] Verify: "Success. No rows returned"

**Verification:**
```sql
SELECT proname FROM pg_proc WHERE proname = 'handle_new_user';
```

Expected: `handle_new_user`

---

### 1.3 Backfill Existing Users (OPTIONAL)

**Only if you have existing Facebook users:**

- [  ] Same SQL Editor window
- [  ] Click **New Query**
- [  ] Copy and paste: `backend/sql/migrations/backfill_facebook_profiles.sql`
- [  ] Click **Run**
- [  ] Check output: Shows how many users were updated

**Verification:**
```sql
SELECT COUNT(*) FROM public.users WHERE facebook_profile IS NOT NULL;
```

---

## Step 2: Backend Deployment

### 2.1 Verify Changes

- [  ] File modified: `backend/app/api/v1/auth.py` (line 2305)
- [  ] Change: Added `"facebook_profile": profile_data.get("facebook_profile")`

### 2.2 Commit Changes

```bash
git status
# Should show: modified: backend/app/api/v1/auth.py
```

- [  ] Changes already committed (see git log)
- [  ] Or commit manually:
```bash
git add backend/app/api/v1/auth.py
git commit -m "feat: Add facebook_profile to /auth/me response"
```

### 2.3 Deploy Backend

- [  ] Push to main branch (if not done already)
- [  ] Wait for DigitalOcean App Platform to deploy
- [  ] Check backend logs for errors

**Verification:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://expert.intelia.com/api/v1/auth/me \
  | jq '.facebook_profile'
```

Expected: `null` or `"https://facebook.com/..."` (not an error)

---

## Step 3: Frontend Deployment

### 3.1 Verify Changes

- [  ] File modified: `frontend/lib/stores/auth.ts`
  - Line 26: Added `facebook_profile?:` string; to `BackendUserData`
  - Line 310: Added `facebookProfile: userData.facebook_profile`
- [  ] File modified: `frontend/types/index.ts`
  - Line 1214: Added `facebookProfile?:` string; to `User` interface

### 3.2 Build and Test Locally

```bash
cd frontend
npm run build
```

- [  ] Build succeeds without TypeScript errors
- [  ] No warnings about `facebook_profile` or `facebookProfile`

### 3.3 Deploy Frontend

- [  ] Push to main branch (if not done already)
- [  ] Wait for deployment to complete
- [  ] Clear browser cache (Ctrl+Shift+R)

---

## Step 4: Testing

### 4.1 Test New Facebook Login

- [  ] Open https://expert.intelia.com in incognito mode
- [  ] Click "Sign in with Facebook"
- [  ] Authorize the application
- [  ] Check database:

```sql
SELECT email, facebook_profile
FROM public.users
WHERE email = 'YOUR_TEST_EMAIL@example.com';
```

**Expected:** `facebook_profile` should contain `https://facebook.com/...`

---

### 4.2 Test API Response

- [  ] Log in with Facebook
- [  ] Open DevTools → Network tab
- [  ] Find `/auth/me` request
- [  ] Check response body

**Expected:** Response contains `"facebook_profile": "https://facebook.com/..."`

---

### 4.3 Test Frontend User Object

- [  ] Log in with Facebook
- [  ] Open DevTools → Console
- [  ] Run:

```javascript
JSON.parse(localStorage.getItem('intelia-auth-store')).state.user.facebookProfile
```

**Expected:** `"https://facebook.com/..."`

---

## Step 5: Monitoring

### 5.1 Check Database

- [  ] Run monitoring query:

```sql
SELECT
  COUNT(*) FILTER (WHERE facebook_profile IS NOT NULL) AS with_facebook,
  COUNT(*) FILTER (WHERE facebook_profile IS NULL) AS without_facebook,
  COUNT(*) AS total
FROM public.users;
```

---

### 5.2 Check Backend Logs

- [  ] Go to DigitalOcean App Platform → Logs
- [  ] Look for errors related to `facebook_profile`
- [  ] Verify no errors in `/auth/me` endpoint

---

### 5.3 Check Frontend Logs

- [  ] Open https://expert.intelia.com
- [  ] Open DevTools → Console
- [  ] Look for errors related to `facebookProfile`
- [  ] Verify user object contains the field

---

## Step 6: Documentation

- [  ] Share `README_FACEBOOK_PROFILE_COMPLETE.md` with team
- [  ] Update internal wiki/docs (if applicable)
- [  ] Notify team that Facebook profile extraction is live

---

## Rollback Plan (If Needed)

If something goes wrong:

### Database Rollback

```sql
-- Remove column
ALTER TABLE public.users DROP COLUMN IF EXISTS facebook_profile;

-- Restore old trigger
-- Re-execute: backend/sql/fixes/fix_handle_new_user_complete_profile.sql
```

### Code Rollback

```bash
# Revert backend changes
git revert <commit-hash>

# Revert frontend changes
git revert <commit-hash>

# Push to main
git push origin main
```

---

## Troubleshooting

### Issue: facebook_profile is NULL

**Check 1:** Verify trigger is updated
```sql
SELECT prosrc FROM pg_proc WHERE proname = 'handle_new_user';
```

Look for: `v_facebook_profile`

**Check 2:** Verify user has Facebook avatar URL
```sql
SELECT raw_user_meta_data->>'avatar_url'
FROM auth.users
WHERE email = 'YOUR_EMAIL';
```

Should contain: `fbsbx.com` and `asid=`

---

### Issue: Frontend doesn't show facebook_profile

**Check 1:** Backend response
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://expert.intelia.com/api/v1/auth/me
```

**Check 2:** TypeScript types
```bash
cd frontend
npm run type-check
```

Should have no errors about `facebookProfile`

---

## Success Criteria

- ✅ New Facebook users have `facebook_profile` populated automatically
- ✅ `/auth/me` returns `facebook_profile` field
- ✅ Frontend `user` object contains `facebookProfile`
- ✅ No errors in backend logs
- ✅ No errors in frontend console
- ✅ TypeScript build succeeds

---

## Final Checklist

- [  ] Database migrations executed
- [  ] Backend deployed
- [  ] Frontend deployed
- [  ] Tests passed
- [  ] Monitoring in place
- [  ] Documentation updated
- [  ] Team notified

---

**Date Completed:** __________________

**Completed By:** __________________

**Notes:**
_________________________________________________________________________
_________________________________________________________________________
_________________________________________________________________________
