# Conversation Sharing - Implementation Guide

**Status**: ✅ Implemented (October 2025)
**Version**: 1.0
**Last Updated**: October 12, 2025

## Overview

This document describes the technical implementation of the conversation sharing feature in Intelia Expert, allowing users to share conversations via public links with optional anonymization and expiration.

## Architecture

### Components

```
Frontend (Next.js)
├── ShareConversationButton.tsx    # Main sharing UI component
└── public/locales/*.json          # i18n translations (12 languages)

Backend (FastAPI)
├── app/api/v1/conversations.py    # Share creation endpoint (authenticated)
└── app/api/v1/shared.py           # Public share access endpoint (no auth)

Database (PostgreSQL)
└── conversation_shares             # Share metadata table
```

## Database Schema

### Table: `conversation_shares`

```sql
CREATE TABLE conversation_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    share_token TEXT UNIQUE NOT NULL,
    created_by TEXT NOT NULL,
    share_type TEXT DEFAULT 'public' CHECK (share_type IN ('public', 'private')),
    anonymize BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    view_count INTEGER DEFAULT 0,
    last_viewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Indexes:**
- `idx_conversation_shares_conversation_id` - Fast lookup by conversation
- `idx_conversation_shares_token` - Fast lookup by share token (public access)
- `idx_conversation_shares_created_by` - User's shares list
- `idx_conversation_shares_expires_at` - Expired shares cleanup

### Schema Location
`backend/sql/schema/create_conversation_shares_table.sql`

## API Endpoints

### 1. Create Share (Authenticated)

**Endpoint**: `POST /api/v1/conversations/{conversation_id}/share`

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "share_type": "public",
  "anonymize": true,
  "expires_in_days": 30
}
```

**Response**:
```json
{
  "share_id": "uuid",
  "share_url": "https://expert.intelia.com/shared/{token}",
  "share_token": "random-secure-token",
  "anonymize": true,
  "expires_at": "2025-11-12T10:30:00Z",
  "created_at": "2025-10-12T10:30:00Z"
}
```

**Implementation**: `backend/app/api/v1/conversations.py:275-355`

**Key Features**:
- Validates conversation ownership
- Generates secure random token (32 bytes, URL-safe)
- Supports optional expiration (7, 30, 90 days, or never)
- Tracks creation metadata

### 2. Access Shared Conversation (Public)

**Endpoint**: `GET /api/v1/shared/{share_token}`

**Authentication**: None (public access)

**Response**:
```json
{
  "status": "success",
  "conversation": {
    "id": "uuid",
    "language": "fr",
    "created_at": "2025-10-12T10:00:00Z",
    "messages": [
      {
        "id": "uuid",
        "role": "user",
        "content": "Question content",
        "sequence_number": 1,
        "created_at": "2025-10-12T10:00:00Z"
      }
    ],
    "message_count": 2
  },
  "share_info": {
    "anonymized": true,
    "shared_by": "Un utilisateur",
    "view_count": 15,
    "expires_at": "2025-11-12T10:30:00Z"
  },
  "timestamp": "2025-10-12T11:00:00Z"
}
```

**Implementation**: `backend/app/api/v1/shared.py:65-212`

**Key Features**:
- No authentication required
- Checks expiration and conversation status
- Anonymizes content if requested (emails, phone numbers)
- Increments view counter
- Hides creator identity if anonymized

### 3. Check Share Health (Public)

**Endpoint**: `GET /api/v1/shared/{share_token}/health`

**Authentication**: None

**Response**:
```json
{
  "status": "valid",
  "valid": true,
  "message": "Partage actif",
  "expires_at": "2025-11-12T10:30:00Z"
}
```

**Implementation**: `backend/app/api/v1/shared.py:215-276`

**Possible Statuses**:
- `valid` - Share is active
- `not_found` - Share doesn't exist
- `deleted` - Conversation was deleted
- `expired` - Share has expired
- `error` - Server error

## Frontend Component

### ShareConversationButton Component

**Location**: `frontend/app/chat/components/ShareConversationButton.tsx`

**Props**:
```typescript
interface ShareConversationButtonProps {
  conversationId: string;
  onShareCreated?: (shareUrl: string) => void;
}
```

**Features**:
- Modal-based UI for configuration
- Options: anonymization, expiration period
- Copy-to-clipboard functionality
- Success/error handling
- Loading states
- **Internationalized** (12 languages)

**Integration**:
```tsx
<ShareConversationButton
  conversationId={conversationId}
  onShareCreated={(url) => console.log('Shared:', url)}
/>
```

**Visibility Conditions**:
- User must be authenticated
- Conversation must exist
- Conversation ID not "welcome" or "temp-*"

**Integration Point**: `frontend/app/chat/page.tsx:1271-1275`

## Internationalization (i18n)

### Translation Keys

All UI text is internationalized using the i18n system:

```typescript
// Translation keys in TranslationKeys interface
"share.button": string;
"share.modalTitle": string;
"share.anonymize": string;
"share.anonymizeHelp": string;
"share.expiration": string;
"share.expiration.7days": string;
"share.expiration.30days": string;
"share.expiration.90days": string;
"share.expiration.never": string;
"share.generating": string;
"share.generate": string;
"share.successTitle": string;
"share.successMessage": string;
"share.copy": string;
"share.copied": string;
"share.error": string;
```

### Supported Languages (12)

| Language | Code | File |
|----------|------|------|
| English | en | `frontend/public/locales/en.json` |
| French | fr | `frontend/public/locales/fr.json` |
| German | de | `frontend/public/locales/de.json` |
| Spanish | es | `frontend/public/locales/es.json` |
| Italian | it | `frontend/public/locales/it.json` |
| Portuguese | pt | `frontend/public/locales/pt.json` |
| Dutch | nl | `frontend/public/locales/nl.json` |
| Polish | pl | `frontend/public/locales/pl.json` |
| Indonesian | id | `frontend/public/locales/id.json` |
| Thai | th | `frontend/public/locales/th.json` |
| Hindi | hi | `frontend/public/locales/hi.json` |
| Chinese | zh | `frontend/public/locales/zh.json` |

**Implementation Commits**:
- `e6b4f424` - Add translations to all 12 locale files
- `93c9788e` - Add TypeScript interface definitions

## Security Considerations

### Token Generation

```python
import secrets

# Generate cryptographically secure random token
share_token = secrets.token_urlsafe(32)  # 32 bytes = 256 bits
```

**Security Properties**:
- URL-safe characters only
- Cryptographically secure random generation
- 256-bit entropy (extremely difficult to guess)
- Unique constraint enforced at database level

### Anonymization

**Anonymized Elements**:
- Email addresses → `[email protégé]`
- Phone numbers → `[téléphone]`
- Creator name → `"Un utilisateur"`

**Implementation**: `backend/app/api/v1/shared.py:16-62`

**Patterns**:
```python
# Email regex
r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# Phone regex (multiple formats)
r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
r'(\+?\d{1,3}[-.\s]?)?(\d{2}[-.\s]?){5}'
```

### Access Control

- **Share Creation**: Requires authentication
- **Share Access**: No authentication (public by design)
- **Ownership Validation**: Only conversation owner can create shares
- **Cascade Delete**: Shares deleted when conversation is deleted
- **Expiration Check**: Automatic validation on every access

## Error Handling

### Common Errors

**404 Not Found**:
- Share token doesn't exist
- Conversation was deleted
- Response: `{"detail": "Partage non trouvé ou conversation supprimée"}`

**410 Gone**:
- Share has expired
- Response: `{"detail": "Ce partage a expiré"}`

**500 Internal Server Error**:
- Database connection issues
- Timezone comparison errors (FIXED in commit 6cd46540)

### Bug Fixes

#### Timezone Comparison Error (CRITICAL FIX)

**Problem**: Comparing timezone-naive datetime with timezone-aware datetime from PostgreSQL.

```python
# ❌ BEFORE (BROKEN)
if share["expires_at"] and share["expires_at"] < datetime.utcnow():

# ✅ AFTER (FIXED)
if share["expires_at"] and share["expires_at"] < datetime.now(timezone.utc):
```

**Commit**: `6cd46540` - "fix: Timezone comparison error in shared conversation endpoint"

**Impact**: Without this fix, all share access attempts fail with "Conversation indisponible".

## Testing

### Manual Testing Checklist

- [ ] Create share with anonymization enabled
- [ ] Create share without anonymization
- [ ] Create share with 7-day expiration
- [ ] Create share with no expiration
- [ ] Access valid share link
- [ ] Access expired share link
- [ ] Access deleted conversation share
- [ ] Access invalid token
- [ ] Verify anonymization works (email/phone hidden)
- [ ] Verify view counter increments
- [ ] Test copy-to-clipboard functionality
- [ ] Test all 12 language translations

### API Testing Examples

```bash
# Create share
curl -X POST https://expert.intelia.com/api/v1/conversations/{id}/share \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"anonymize": true, "expires_in_days": 30}'

# Access share (public)
curl https://expert.intelia.com/api/v1/shared/{token}

# Check health (public)
curl https://expert.intelia.com/api/v1/shared/{token}/health
```

## Performance Considerations

### Database Indexes

All critical queries are indexed:
- Share token lookup: O(log n) with `idx_conversation_shares_token`
- Conversation shares list: O(log n) with `idx_conversation_shares_conversation_id`
- User shares: O(log n) with `idx_conversation_shares_created_by`

### Caching Opportunities

**Not Implemented (Future Enhancement)**:
- Cache frequently accessed shares
- Cache anonymization results
- TTL based on expiration time

## Deployment

### Required Steps

1. **Run SQL Schema**:
   ```bash
   psql $DATABASE_URL -f backend/sql/schema/create_conversation_shares_table.sql
   ```

2. **Deploy Backend**:
   - Ensure `backend/app/api/v1/shared.py` is deployed
   - Verify router registration in `backend/app/main.py`

3. **Deploy Frontend**:
   - Ensure all locale files include share.* keys
   - Verify ShareConversationButton is integrated

4. **Verify**:
   ```bash
   curl https://expert.intelia.com/api/v1/shared/test/health
   # Should return 404 for invalid token (expected)
   ```

### Environment Variables

No additional environment variables required. Uses existing:
- `DATABASE_URL` - PostgreSQL connection string
- Standard FastAPI configuration

## Known Limitations

1. **No Password Protection**: All public shares are accessible by anyone with the link
2. **No Deletion**: Users cannot delete shares after creation (manual DB deletion required)
3. **No Edit**: Cannot modify share settings after creation (must create new share)
4. **No Analytics**: View tracking is basic (count + last viewed time)
5. **No Rate Limiting**: No rate limiting on share access endpoint

## Future Enhancements

### Planned Features
- [ ] Share deletion endpoint
- [ ] Share list endpoint (user's shares)
- [ ] Password-protected shares
- [ ] Share edit functionality
- [ ] Advanced analytics (viewer locations, devices)
- [ ] Email notifications on share access
- [ ] Share templates (presets for common scenarios)

### Performance Improvements
- [ ] Redis caching for hot shares
- [ ] Rate limiting on public endpoint
- [ ] CDN caching for static share pages

## Related Documentation

- [Conversation Sharing User Guide](./CONVERSATION_SHARING_GUIDE.md)
- [Database Schema](./DATABASE_SCHEMA.md)
- [API Documentation](../backend/API_DOCUMENTATION.md)
- [Fix Missing Titles](../backend/FIX_MISSING_TITLES_README.md)
- [SQL Scripts Organization](../../backend/sql/README.md)

## Changelog

### October 12, 2025
- ✅ Initial implementation complete
- ✅ Database schema created
- ✅ Backend API endpoints implemented
- ✅ Frontend component created
- ✅ Internationalization added (12 languages)
- ✅ Timezone bug fixed
- ✅ Documentation created

## Support

For issues or questions:
1. Check [known limitations](#known-limitations)
2. Review [error handling](#error-handling) section
3. Verify [deployment steps](#deployment) completed
4. Check PostgreSQL logs for errors
5. Contact development team

---

**Maintainer**: Development Team
**Last Review**: October 12, 2025
