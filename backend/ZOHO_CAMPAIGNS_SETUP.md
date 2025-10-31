# Zoho Campaigns Integration Setup

## Overview

The Zoho Campaigns integration automatically synchronizes new user registrations to a Zoho Campaigns mailing list. When a user registers, their information (email, first name, last name, country, etc.) is pushed to Zoho.

## Required Environment Variables

Add these variables to your `.env` file or Digital Ocean environment variables:

```bash
# Zoho Campaigns OAuth Credentials
ZOHO_CLIENT_ID=your_client_id_here
ZOHO_CLIENT_SECRET=your_client_secret_here
ZOHO_REFRESH_TOKEN=your_refresh_token_here

# Zoho Configuration
ZOHO_REGION=com  # Options: com (US), eu (Europe), in (India), au (Australia), jp (Japan)
ZOHO_CAMPAIGNS_LIST_KEY=your_list_key_here
```

## How to Obtain Credentials

### 1. Create OAuth Client in Zoho API Console

1. Go to **https://api-console.zoho.com/**
2. Sign in with your Zoho account
3. Click **"Add Client"**
4. Choose **"Self Client"** (simplest option for server-to-server)
5. Define scopes:
   - `ZohoCampaigns.contact.ALL`
   - `ZohoCampaigns.campaign.ALL` (optional)
6. Click **"Create"**
7. Copy your **Client ID** and **Client Secret**

### 2. Generate Refresh Token

1. In the API Console, click on your client
2. Go to **"Generate Code"** tab
3. Select the scopes you defined earlier
4. Set **Time Duration** to 3-10 minutes
5. Click **"Generate"**
6. **IMMEDIATELY COPY THE CODE** (it expires quickly!)

7. Exchange the code for a refresh token using this curl command:

```bash
curl -X POST "https://accounts.zoho.com/oauth/v2/token" \
  -d "code=YOUR_GENERATED_CODE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=https://expert-app-cngws.ondigitalocean.app/oauth/callback" \
  -d "grant_type=authorization_code"
```

Response will include:
```json
{
  "access_token": "...",
  "refresh_token": "1000.abc123...",  // ← THIS IS WHAT YOU NEED
  "expires_in": 3600
}
```

8. Copy the **refresh_token** value (starts with `1000.`)

### 3. Get Your Campaigns List Key for "Intelia Cognito"

1. Log into **Zoho Campaigns**
2. Go to **"Contacts"** → **"Mailing Lists"**
3. Find and click on the list named **"Intelia Cognito"**
   - If this list doesn't exist yet, create it first:
     - Click **"Create Mailing List"**
     - Name: **Intelia Cognito**
     - Click **"Create"**
4. Copy the **List Key** from the URL:
   - URL format: `https://campaigns.zoho.com/campaigns/OrgViewMailingList.zc?listkey=ABC123XYZ`
   - Your list key is: `ABC123XYZ`

**IMPORTANT**: Make sure you're using the list key for "Intelia Cognito" specifically.

## Syncing Existing Users (One-Time Setup)

The integration only syncs **NEW** users who register after configuration. To sync existing users already in your database, use the provided script:

### 1. Test First (Dry Run)

```bash
cd backend
python scripts/sync_existing_users_to_zoho.py --dry-run --limit 5
```

This will show what would happen without making changes.

### 2. Sync a Few Users (Test)

```bash
python scripts/sync_existing_users_to_zoho.py --limit 10
```

This syncs only 10 users to verify everything works.

### 3. Sync All Users

```bash
python scripts/sync_existing_users_to_zoho.py
```

This syncs ALL existing users to the "Intelia Cognito" list in Zoho Campaigns.

**Notes**:
- The script automatically handles duplicates (won't re-add existing contacts)
- Rate limiting is built-in (~170 requests/minute to respect Zoho's 200/min limit)
- Progress is shown for each user
- Run this **ONCE** after initial setup

### Script Output Example:

```
[1/150] user1@example.com
  ✅ Ajouté à Zoho
[2/150] user2@example.com
  ℹ️  Déjà existant dans Zoho
[3/150] user3@example.com
  ✅ Ajouté à Zoho
...
================================================================================
RÉSUMÉ DE LA SYNCHRONISATION
================================================================================
Total traités:        150
✅ Nouveaux ajoutés:  145
ℹ️  Déjà existants:    5
❌ Erreurs:           0
================================================================================
```

## Testing the Integration

### Test with curl:

```bash
# Test user registration (will sync to Zoho)
curl -X POST "https://expert-app-cngws.ondigitalocean.app/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "first_name": "Test",
    "last_name": "User",
    "country": "CA",
    "preferred_language": "en"
  }'
```

### Check Logs:

Look for these log messages in backend logs:

```
✅ [Register] ✅ Zoho Campaigns sync successful: test@example.com
```

Or if not configured:
```
⊘ [Zoho] Service non configuré - contact non synchronisé
```

## Troubleshooting

### Error: "Invalid refresh token"
- Your refresh token may have expired or been revoked
- Regenerate a new refresh token following steps above

### Error: "List key not found"
- Verify your `ZOHO_CAMPAIGNS_LIST_KEY` is correct
- Ensure the list exists in your Zoho Campaigns account

### Error: "Contact already exists" (Code 1006)
- This is normal! The service will log it as successful
- Zoho won't create duplicates

### No errors but users not syncing
- Check that all 4 environment variables are set
- Verify the service is configured: look for log message about service availability

## Data Synced to Zoho

When a user registers, these fields are synced:

| User Field | Zoho Field | Required |
|------------|------------|----------|
| email | Contact Email | Yes |
| first_name | First Name | No |
| last_name | Last Name | No |
| country | Country | No |
| company | Company | No |
| phone | Phone | No |
| preferred_language | Language | No |
| production_type | Production Type | No |
| category | Category | No |

## Security Notes

- ⚠️ **NEVER** commit your credentials to git
- Store credentials in environment variables only
- Use different Zoho clients for dev/staging/production
- Rotate refresh tokens periodically for security

## Implementation Details

**Service**: `backend/app/services/zoho_campaigns_service.py`
**Integration Point**: `backend/app/api/v1/auth.py` - `/register` endpoint
**Behavior**:
- Synchronous (blocks registration if Zoho times out)
- Non-blocking (registration succeeds even if Zoho fails)
- Automatic retry: NO (fails gracefully)
- Rate limiting: Handled by Zoho (typically 200 requests/minute)

## Support

For Zoho API documentation:
- https://www.zoho.com/campaigns/help/developers/api-overview.html
- https://www.zoho.com/campaigns/help/developers/add-contacts.html
