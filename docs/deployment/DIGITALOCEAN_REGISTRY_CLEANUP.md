# DigitalOcean Container Registry - Automatic Cleanup Guide

**Version:** 1.0.0
**Last Updated:** 2025-10-28
**Status:** ✅ Production-ready

## Overview

This guide documents the automatic cleanup mechanism for DigitalOcean Container Registry (DOCR) implemented in our GitHub Actions CI/CD pipeline. The cleanup process prevents storage accumulation by automatically deleting old container image tags while keeping the most recent versions.

---

## Problem Statement

### Initial Issue

DigitalOcean Container Registry accumulated old Docker image tags with each deployment, leading to:
- **Storage bloat**: 45+ images per repository
- **Increased costs**: Registry storage charges
- **Slower operations**: Longer image pull/push times
- **Management overhead**: Manual cleanup required

### Failed Attempts

Several approaches were tried before finding the working solution:

1. **Attempt 1: Tag count with newlines** ❌
   ```bash
   TAG_COUNT=$(echo "$TAGS" | jq '. | length')
   # Result: "1\n0" - integer expression error
   ```

2. **Attempt 2: Using registry prefix in repository name** ❌
   ```bash
   doctl registry repository list-tags ${{ secrets.DOCR_NAME }}/frontend
   # Result: 404 - repository not found (URL encoded as %2F)
   ```

3. **Attempt 3: Using full output from list-tags** ❌
   ```bash
   doctl ... | while read -r tag; do
     doctl registry repository delete-tag frontend "$tag" --force
   done
   # Result: 422 "invalid tag: invalid tag format"
   # Reason: $tag contained full metadata instead of just tag name
   ```

---

## Working Solution

### Root Cause

The `doctl registry repository list-tags` command with `--format Tag --no-header` still returns **full metadata** for each tag:

```
main-c4856bbbc0de...    3.43 kB    2025-10-28 23:47:42 +0000 UTC    sha256:b2b7ee925cf...
```

The script was passing this entire line to `delete-tag`, which expects **only the tag name** (first column).

### Fix Applied

Add `awk '{print $1}'` to extract only the first column (tag name) before deletion:

```bash
# ✅ CORRECT APPROACH
doctl registry repository list-tags frontend --format Tag --no-header \
  | tail -n +11 \
  | awk '{print $1}' \
  | while read -r tag; do
      if [ ! -z "$tag" ] && [ "$tag" != "latest" ] && [ "$tag" != "buildcache" ]; then
        echo "Deleting tag: $tag"
        doctl registry repository delete-tag frontend "$tag" --force || echo "Failed to delete $tag"
      fi
    done
```

**Key insight**: Even with `--format Tag`, doctl returns tabular data with whitespace-separated columns. The `awk '{print $1}'` extracts just the tag name.

---

## Implementation Details

### Cleanup Script Structure

The cleanup is implemented as part of `.github/workflows/deploy.yml` in the `cleanup-registry` job:

```yaml
cleanup-registry:
  needs:
    - build-frontend
    - build-backend
    - build-rag
    - build-llm
    - build-prometheus
  if: always() && !cancelled()
  runs-on: ubuntu-latest
  steps:
    - name: Install doctl
      uses: digitalocean/action-doctl@v2
      with:
        token: ${{ secrets.DO_API_TOKEN }}

    - name: Cleanup old frontend tags
      if: needs.build-frontend.result == 'success'
      run: |
        echo "Cleaning up old frontend tags (keeping 10 most recent)..."

        # Count total tags
        TAG_COUNT=$(doctl registry repository list-tags frontend --format Tag --no-header | wc -l | tr -d ' ')
        echo "Found $TAG_COUNT tags total"

        # Only cleanup if we have more than 10 tags
        if [ "$TAG_COUNT" -gt 10 ]; then
          TAGS_TO_DELETE=$(($TAG_COUNT - 10))
          echo "Deleting $TAGS_TO_DELETE old tags..."

          # Extract only the tag name (first column) using awk
          doctl registry repository list-tags frontend --format Tag --no-header \
            | tail -n +11 \
            | awk '{print $1}' \
            | while read -r tag; do
              if [ ! -z "$tag" ] && [ "$tag" != "latest" ] && [ "$tag" != "buildcache" ]; then
                echo "Deleting tag: $tag"
                doctl registry repository delete-tag frontend "$tag" --force || echo "Failed to delete $tag"
              fi
            done
        else
          echo "Only $TAG_COUNT tags found, no cleanup needed (keeping all)"
        fi
```

### Services Covered

The cleanup is applied to all 5 services:
- ✅ `frontend`
- ✅ `backend`
- ✅ `rag`
- ✅ `llm`
- ✅ `prometheus`

### Retention Policy

- **Keep**: 10 most recent tags per repository
- **Protect**: `latest` and `buildcache` tags are never deleted
- **Delete**: All tags beyond the 10 most recent (sorted by update time)

---

## Technical Explanation

### Why `awk '{print $1}'` Works

The `list-tags` output is whitespace-delimited with multiple columns:

```
Column 1: Tag name (main-abc123...)
Column 2: Size (3.43 kB)
Column 3-4: Date (2025-10-28 23:47:42)
Column 5: Timezone (+0000 UTC)
Column 6: SHA (sha256:b2b7ee...)
```

**awk behavior**:
- `'{print $1}'`: Extracts only the first field (tag name)
- Default delimiter: Whitespace (spaces/tabs)
- Output: Clean tag name without metadata

### Command Breakdown

```bash
doctl registry repository list-tags frontend --format Tag --no-header \
  | tail -n +11 \
  | awk '{print $1}' \
  | while read -r tag; do ...
```

1. **list-tags**: Get all tags for `frontend` repository
2. **tail -n +11**: Skip first 10 lines (keep 10 most recent)
3. **awk '{print $1}'**: Extract only tag name from each line
4. **while read**: Iterate over each tag name
5. **delete-tag**: Delete the tag

### Error Handling

```bash
doctl registry repository delete-tag frontend "$tag" --force || echo "Failed to delete $tag"
```

- `--force`: Skip confirmation prompts (required for automation)
- `|| echo`: Continue on error, log failure instead of stopping

---

## Garbage Collection

After deleting tags, run garbage collection to actually free storage:

```yaml
- name: Run garbage collection
  run: |
    echo "Running garbage collection to free up storage..."
    doctl registry garbage-collection start --include-untagged-manifests --force || true
```

**Important**: Deleting tags only removes the reference. Garbage collection deletes the actual image layers from storage.

---

## Verification

### Check Current Tags

```bash
# List all tags for a repository
doctl registry repository list-tags frontend

# Count tags
doctl registry repository list-tags frontend --format Tag --no-header | wc -l
```

### Expected Output After Cleanup

```
Cleaning up old frontend tags (keeping 10 most recent)...
Found 21 tags total
Deleting 11 old tags...
Deleting tag: main-c4856bbbc0de1c4bb321dd28c39d641202aa9c4d
Deleting tag: main-3ea193334fec63be39e75bd1a2212d106cda3783
...
Running garbage collection to free up storage...
```

### Post-Cleanup Verification

```bash
# Should show ~10 tags per repository
doctl registry repository list-tags frontend --format Tag
doctl registry repository list-tags backend --format Tag
doctl registry repository list-tags rag --format Tag
doctl registry repository list-tags llm --format Tag
doctl registry repository list-tags prometheus --format Tag
```

---

## Cost Impact

### Before Cleanup
- **45 images** per repository × 5 services = **225 total images**
- Average image size: ~500 MB
- Total storage: ~112 GB
- Estimated monthly cost: **$5-10** (DigitalOcean charges $0.02/GB/month after free tier)

### After Cleanup
- **10 images** per repository × 5 services = **50 total images**
- Total storage: ~25 GB
- Estimated monthly cost: **~$0** (within free tier)
- **Savings**: ~$5-10/month

---

## Maintenance

### Adjusting Retention

To keep more or fewer tags, modify the threshold:

```bash
# Keep 10 tags (current)
if [ "$TAG_COUNT" -gt 10 ]; then
  TAGS_TO_DELETE=$(($TAG_COUNT - 10))
  doctl ... | tail -n +11 | ...

# Keep 20 tags (example)
if [ "$TAG_COUNT" -gt 20 ]; then
  TAGS_TO_DELETE=$(($TAG_COUNT - 20))
  doctl ... | tail -n +21 | ...
```

### Manual Cleanup (Emergency)

If automatic cleanup fails, run manually:

```bash
# Authenticate
doctl auth init

# List old tags
doctl registry repository list-tags frontend --format Tag --no-header | tail -n +11

# Delete specific tag
doctl registry repository delete-tag frontend TAG_NAME --force

# Run garbage collection
doctl registry garbage-collection start --include-untagged-manifests --force
```

---

## Troubleshooting

### Issue: "invalid tag: invalid tag format" (422 error)

**Cause**: Passing full metadata line instead of just tag name.

**Solution**: Ensure `awk '{print $1}'` is present in the pipeline.

### Issue: "repository not found" (404 error)

**Cause**: Using registry prefix in repository name (e.g., `cognito-registry/frontend`).

**Solution**: Use only repository name (e.g., `frontend`).

### Issue: Tags not being deleted

**Possible causes**:
1. Conditional not met (`needs.build-X.result == 'success'`)
2. Tag count ≤ 10 (no cleanup needed)
3. Tag is `latest` or `buildcache` (protected)

**Debug**:
```bash
# Check GitHub Actions logs
# Look for: "Cleaning up old X tags (keeping 10 most recent)..."
```

---

## References

- [doctl registry repository delete-tag documentation](https://docs.digitalocean.com/reference/doctl/reference/registry/repository/delete-tag/)
- [DigitalOcean Container Registry pricing](https://www.digitalocean.com/pricing/container-registry)
- [GitHub Actions workflow file](../../.github/workflows/deploy.yml)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-28 | Initial documentation after successful fix |

---

## Contributors

- Claude Code (Anthropic) - Implementation and documentation
- Dominic Desy - Testing and validation
