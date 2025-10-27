# Version Management System

## Overview

This document describes the centralized version management system for Intelia Expert. The system provides both application-level versioning and file-level versioning with full automation through GitHub Actions.

## Version Structure

### Application Version
- **Location**: `VERSION` file at project root
- **Current Version**: 1.4.1
- **Format**: Semantic versioning (MAJOR.MINOR.PATCH)
  - MAJOR: Breaking changes
  - MINOR: New features (backward compatible)
  - PATCH: Bug fixes

### File Versions
Each production file contains a version header:

**Python files** (.py):
```python
"""
Module Name
Version: 1.4.1
Last modified: 2025-10-26
"""
```

**TypeScript/JavaScript files** (.ts, .tsx, .jsx):
```typescript
/**
 * Module Name
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
```

## How It Works

### Local Development

When developing locally, the version API (`/api/v1/version`) reads from:
1. VERSION file in the project root
2. Returns current timestamp for build_date
3. Returns "local" for commit SHA

### Production Deployment

#### 1. GitHub Actions Build Process

When code is pushed to the `main` branch:

1. **Read VERSION file**: Each build job reads the VERSION file
   ```yaml
   - name: Read VERSION file
     id: version
     run: echo "VERSION=$(cat VERSION)" >> $GITHUB_OUTPUT
   ```

2. **Inject Build Arguments**: Docker build receives three arguments:
   ```yaml
   build-args: |
     BUILD_VERSION=${{ steps.version.outputs.VERSION }}
     BUILD_DATE=${{ github.event.head_commit.timestamp }}
     COMMIT_SHA=${{ github.sha }}
   ```

3. **Docker Build**: Dockerfiles accept these arguments and set them as environment variables:
   ```dockerfile
   ARG BUILD_VERSION=unknown
   ARG BUILD_DATE=unknown
   ARG COMMIT_SHA=unknown

   ENV BUILD_VERSION=${BUILD_VERSION} \
       BUILD_DATE=${BUILD_DATE} \
       COMMIT_SHA=${COMMIT_SHA}
   ```

#### 2. Runtime in Production

The running container has these environment variables set:
- `BUILD_VERSION`: e.g., "1.4.1"
- `BUILD_DATE`: ISO timestamp from the commit
- `COMMIT_SHA`: Full Git commit hash

The version API reads these environment variables and returns:
```json
{
  "version": "1.4.1",
  "build_date": "2025-10-26T15:30:45Z",
  "commit": "a1b2c3d"
}
```

## API Endpoint

### GET /api/v1/version

Returns application version information.

**Response:**
```json
{
  "version": "1.4.1",
  "build_date": "2025-10-26T15:30:45Z",
  "commit": "a1b2c3d"
}
```

**Fields:**
- `version`: Application version from VERSION file
- `build_date`: ISO timestamp when the build was created
- `commit`: Short Git commit SHA (7 characters)

## Frontend Integration

The About page (`frontend/app/about/page.tsx`) displays the version dynamically:

```typescript
const [version, setVersion] = useState("1.4.1");

useEffect(() => {
  fetch("/api/v1/version")
    .then((res) => res.json())
    .then((data) => setVersion(data.version))
    .catch(() => setVersion("1.4.1"));
}, []);
```

## How to Update the Version

### 1. Update VERSION File

Edit the `VERSION` file at the project root:
```bash
echo "1.5.0" > VERSION
```

### 2. Update File Headers

Use the version header update script:
```bash
python add_version_headers.py --version 1.5.0
```

This will update all production files with the new version and current date.

### 3. Commit and Push

```bash
git add VERSION
git add backend/ frontend/ llm/ prometheus-service/
git commit -m "chore: Bump version to 1.5.0"
git push origin main
```

### 4. Automatic Deployment

GitHub Actions will:
1. Read the new version from VERSION file
2. Build Docker images with the version metadata
3. Deploy to Digital Ocean
4. The API will return the new version

## Files Modified

### GitHub Actions
- `.github/workflows/deploy.yml`: Injects version metadata into all service builds

### Dockerfiles
- `backend/Dockerfile`: Accepts and sets BUILD_VERSION, BUILD_DATE, COMMIT_SHA
- `llm/Dockerfile`: Accepts and sets BUILD_VERSION, BUILD_DATE, COMMIT_SHA
- `frontend/Dockerfile`: Accepts and sets BUILD_VERSION, BUILD_DATE, COMMIT_SHA
- `prometheus-service/Dockerfile`: Accepts and sets BUILD_VERSION, BUILD_DATE, COMMIT_SHA

### Backend
- `backend/app/api/v1/version.py`: Version API endpoint
- `backend/app/api/v1/__init__.py`: Mounts version router

### Frontend
- `frontend/app/about/page.tsx`: Displays dynamic version

### Scripts
- `add_version_headers.py`: Batch update file version headers
- `test_version_headers.py`: Test version header updates on sample files

### Documentation
- `VERSION`: Application version file
- `VERSION_MANAGEMENT.md`: This documentation

## Production Files Versioned

Total: 447 files across:
- Backend: `backend/app/**/*.py`
- LLM Service: `llm/**/*.py`
- Frontend: `frontend/**/*.{ts,tsx,jsx}`
- Prometheus: `prometheus-service/**/*.py` (if any)

**Excluded from versioning:**
- Tests (`**/tests/**`, `**/*_test.py`, `**/*.test.ts`)
- Scripts (`scripts/**`)
- SQL files (`**/*.sql`)
- Node modules (`node_modules/**`)
- Documentation (`*.md`, `docs/**`)
- Cache directories (`__pycache__/**`, `.next/**`)

## Version History

| Version | Date       | Changes                                    |
|---------|------------|--------------------------------------------|
| 1.4.1   | 2025-10-26 | Initial version management system          |

## Best Practices

1. **Semantic Versioning**: Follow semver (MAJOR.MINOR.PATCH)
2. **Commit Messages**: Use conventional commits (e.g., "chore: Bump version to X.Y.Z")
3. **Changelog**: Update CHANGELOG.md when bumping versions
4. **Testing**: Test locally before pushing version changes
5. **Automation**: Let GitHub Actions handle the deployment - don't manually modify environment variables

## Troubleshooting

### Version shows "unknown" in production
- Check if GitHub Actions successfully read the VERSION file
- Verify build arguments are passed in `.github/workflows/deploy.yml`
- Confirm Dockerfile accepts and sets the environment variables

### Version shows "local" instead of commit SHA
- This is expected in local development
- In production, verify `COMMIT_SHA` environment variable is set

### About page shows old version
- Clear browser cache
- Check if the frontend successfully built with new version
- Verify API endpoint returns correct version: `curl /api/v1/version`

## Future Enhancements

- [ ] Add version endpoint to LLM service
- [ ] Display build date and commit in admin dashboard
- [ ] Create automated version bumping script
- [ ] Add version to logs for better debugging
- [ ] Track version changes in database for audit trail
