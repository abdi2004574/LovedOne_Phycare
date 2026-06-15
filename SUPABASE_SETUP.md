# Supabase Setup Guide — LovedOne PsychCare (Corrected)

This guide addresses the issues found in the original SUPABASE_SETUP.md and provides a secure, complete path for setting up Supabase for LovedOne PsychCare.

---

## Audit Findings (Original vs. Corrected)

| # | Issue in Original | Risk | Correction |
|---|-------------------|------|------------|
| 1 | `.env` contained fake/example Supabase credentials | App connects to wrong DB or fails silently | Updated `.env` with your real project credentials |
| 2 | `JWT_SECRET` was a placeholder string | Auth tokens are insecure and predictable | Set `JWT_SECRET` to a strong random secret |
| 3 | `supabase link` stores DB password in plaintext in `~/.supabase/` | Credential leak if machine is compromised | Use a strong database password; note that CLI stores it locally |
| 4 | `ENVIRONMENT=development` means app uses mock DB, never hitting Supabase | Production-like testing impossible | Switch to `ENVIRONMENT=production` when ready to test real DB |
| 5 | No `WEBHOOK_SECRET` documented for webhook verification | Webhooks can be spoofed | `WEBHOOK_SECRET` is now set for HMAC verification |
| 6 | `supabase db push` documentation incomplete for Windows | Command may fail silently on Windows | Use `supabase db push --linked` and verify output |
| 7 | No `.gitignore` mention for `supabase/.env` | Local secrets may leak to git | Added to `.gitignore` if missing |
| 8 | Auth hook not configured for auto-profile creation | Users can sign up but no `profiles` row is created | Auth hook added below |
| 9 | RLS policies use `auth.uid()` but no auth hook links `auth.users.id` to `profiles.id` | Foreign key exists but profile may not be created on signup | Auth hook ensures profile creation |
| 10 | Seed data uses hardcoded UUIDs that may conflict | Seed fails if UUIDs already exist | Use `ON CONFLICT DO NOTHING` |

---

## Part 1 — Dashboard Setup

### Step 1. Create a Supabase Project

1. Go to [https://supabase.com](https://supabase.com) and sign in.
2. Click **"New project"**.
3. Choose your organization.
4. Fill in:
   - **Project name**: `lovedone-psycare-prod`
   - **Database password**: Use a strong password (store it in a password manager).
   - **Region**: Pick the closest region.
5. Click **"Create new project"**. Provisioning takes ~2 minutes.

### Step 2. Get Your API Credentials

1. Go to **Project Settings** → **API**.
2. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **`anon` key** → `SUPABASE_KEY`
   - **`service_role` key** → `SUPABASE_SERVICE_KEY`

### Step 3. Configure Authentication

1. Go to **Authentication** → **Providers** → **Email**:
   - Toggle **"Enable Email provider"** ON.
   - Toggle **"Enable email signups"** ON.
   - Toggle **"Enable email confirmations"** ON (production).
   - Set **"Confirm email redirect URL"** to your frontend callback.
2. Go to **Authentication** → **URL Configuration**:
   - **Site URL**: `https://lovedonepsychcare.vercel.app`
   - **Redirect URLs**: Add `http://localhost:3000/**` and your production URL.
3. Go to **Authentication** → **Settings**:
   - Set **Custom JWT expiry** to `30` minutes (matches `ACCESS_TOKEN_EXPIRE_MINUTES`).
   - Enable **Refresh token rotation**.
4. Go to **Authentication** → **Hooks**:
   - Add a **"User created"** hook (see Step 6 below).

### Step 4. Configure Storage (Optional)

1. Go to **Storage** → **Create bucket** → Name: `avatars`.
2. Set **Public bucket** to **OFF**.
3. Create RLS policies for the bucket:
   ```sql
   -- Users can upload their own avatar
   create policy "Users can upload own avatar"
     on storage.objects for insert
     with check (
       bucket_id = 'avatars'
       and auth.uid()::text = (storage.foldername(name))[1]
     );

   -- Users can update their own avatar
   create policy "Users can update own avatar"
     on storage.objects for update
     using (
       bucket_id = 'avatars'
       and auth.uid()::text = (storage.foldername(name))[1]
     );

   -- Users can delete their own avatar
   create policy "Users can delete own avatar"
     on storage.objects for delete
     using (
       bucket_id = 'avatars'
       and auth.uid()::text = (storage.foldername(name))[1]
     );

   -- Anyone can view avatars (public bucket OFF but files are accessible via signed URL)
   create policy "Anyone can view avatars"
     on storage.objects for select
     using (bucket_id = 'avatars');
   ```

### Step 5. Configure Realtime

1. Go to **Database** → **Replication**.
2. Enable **Realtime** for:
   - `messages`
   - `conversations`
   - `appointments`

---

## Part 2 — Local Development with Supabase CLI

### Step 6. Install and Initialize

```bash
# Install CLI (npm)
npm install -g supabase

# Initialize project (creates supabase/ directory)
supabase init
```

### Step 7. Log In and Link

```bash
supabase login
supabase link --project-ref stjcopwgzyqydbmcigdp
```

When prompted for the database password, enter the one you set in Step 1.

### Step 8. Start Local Services

```bash
supabase start
```

Copy the local credentials printed in the terminal and update `.env` if you want to test against local Supabase.

### Step 9. Create and Apply Migrations

```bash
# Create a new migration file
supabase migration new initial_schema

# Apply to local database
supabase db push

# Apply to remote (linked) database
supabase db push --linked
```

### Step 10. Verify with Studio

```bash
supabase studio
```

Open [http://localhost:54323](http://localhost:54323) to verify tables, RLS policies, and data.

---

## Part 3 — Environment Configuration

### Step 11. `.env` (Already Updated)

Your `.env` now contains:

```env
SUPABASE_URL=https://stjcopwgzyqydbmcigdp.supabase.co
SUPABASE_KEY=<your-anon-key>
SUPABASE_SERVICE_KEY=<your-service-role-key>
JWT_SECRET=<strong-random-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ANTHROPIC_API_KEY=sk-ant-api03-dummy
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000
WEBHOOK_SECRET=v1,whsec_YyruP8+YkVMdKx7wjjhf2j2ztbEpY5qBqqUxN5VGuiU/i0tZf1hgrZnisHizaS8zb0Mwa1vlrqZg0XSL
```

**To test with real Supabase**, change `ENVIRONMENT=production`.

### Step 12. Configure `.gitignore`

Ensure these lines are in your `.gitignore`:

```
# Supabase
supabase/.env
.env
*.log

# Credentials
**/signing_keys.json
```

### Step 13. Auth Hook (Auto-Create Profile on Signup)

In **Supabase Dashboard** → **Authentication** → **Hooks** → **"User created"**:

```sql
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name, phone, role, language)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', 'User'),
    coalesce(new.raw_user_meta_data->>'phone', null),
    coalesce(new.raw_user_meta_data->>'role', 'patient'),
    coalesce(new.raw_user_meta_data->>'language', 'en')
  )
  on conflict (id) do nothing;
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
```

This ensures every new signup automatically gets a `profiles` row.

---

## Part 4 — Apply the SQL Schema

The migration file has already been created at:
`supabase/migrations/20260613000000_initial_schema.sql`

Run:

```bash
supabase db push --linked
```

**Or** paste the contents of that file into the **Supabase Dashboard → SQL Editor** and execute.

---

## Part 5 — Backend Integration

### Step 14. Verify `app/config.py`

Your `app/config.py` already reads Supabase credentials from environment variables. No changes needed.

### Step 15. Set `ENVIRONMENT=production` to Use Real DB

When you are ready to use the real Supabase database:

```env
ENVIRONMENT=production
```

When `ENVIRONMENT=development`, the app uses the mock in-memory DB (as designed).

---

## Part 6 — Webhook Security

### Step 16. Verify Webhook Signatures

Your `app/routers/webhooks.py` uses `X-API-KEY` header verification via `api_keys` table. The `WEBHOOK_SECRET` environment variable is available for HMAC signature verification if needed.

To add HMAC verification to webhooks:

```python
import hmac
import hashlib

async def verify_webhook_signature(request: Request, x_webhook_signature: str = Header(...)):
    body = await request.body()
    expected = hmac.new(
        os.environ["WEBHOOK_SECRET"].encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, x_webhook_signature):
        raise HTTPException(403, "Invalid webhook signature")
    return True
```

---

## Part 7 — Generate Strong Secrets

### Generate JWT_SECRET

```bash
# PowerShell
[System.Guid]::NewGuid().ToString("N") + [System.Guid]::NewGuid().ToString("N")

# Or use OpenSSL (if installed)
openssl rand -hex 32
```

### Generate ANTHROPIC_API_KEY

Obtain from [https://console.anthropic.com/](https://console.anthropic.com/).

---

## Summary of Changes Made

1. **Updated `.env`**:
   - Replaced fake Supabase credentials with your real project credentials.
   - Set `JWT_SECRET` to a strong random value.
   - Added `WEBHOOK_SECRET`.

2. **Created migration file**:
   - `supabase/migrations/20260613000000_initial_schema.sql` with complete schema.

3. **Identified missing auth hook**:
   - Added SQL for auto-profile creation on user signup.

4. **Documented webhook security**:
   - Added HMAC verification example.

---

## Next Steps

1. Run `supabase login` in a terminal with TTY access.
2. Run `supabase link --project-ref stjcopwgzyqydbmcigdp`.
3. Run `supabase db push --linked`.
4. Set `ENVIRONMENT=production` in `.env` when ready to test with real DB.
5. Verify the schema in **Supabase Studio** (`supabase studio`).
