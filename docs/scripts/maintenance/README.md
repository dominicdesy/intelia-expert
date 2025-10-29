# Maintenance Scripts

This directory contains utility scripts for maintaining the Intelia Expert codebase.

## Translation Management Scripts

### `update_i18n_interface.py`
**Purpose**: Regenerates the TypeScript `TranslationKeys` interface from the English translation JSON file.

**Usage**:
```bash
python docs/scripts/maintenance/update_i18n_interface.py
```

**When to use**:
- After adding new translation keys to `frontend/public/locales/en.json`
- When TypeScript compilation fails due to missing translation keys
- To ensure the TypeScript interface stays synchronized with JSON files

**What it does**:
1. Reads all keys from `frontend/public/locales/en.json`
2. Flattens nested JSON to dot notation (e.g., `history.search`)
3. Generates TypeScript interface with all keys
4. Updates `frontend/lib/languages/i18n.ts` in place

**Output**: Updates the `TranslationKeys` interface with all current translation keys.

---

### `add_search_translations.py`
**Purpose**: Adds conversation search translation keys to all 16 language files.

**Usage**:
```bash
python docs/scripts/maintenance/add_search_translations.py
```

**Languages supported**: en, fr, es, pt, de, it, zh, ja, nl, pl, ar, hi, th, vi, tr, id

**Keys added**:
- `history.searchPlaceholder`
- `history.searching`
- `history.searchError`
- `history.noSearchResults`
- `history.tryDifferentSearch`
- `history.resultsFound`

**What it does**:
1. Defines translations for all 16 languages
2. Finds the insertion point after `history.search` key
3. Inserts the 6 new keys with proper JSON formatting
4. Updates all language files in `frontend/public/locales/`

---

### `add_missing_translation_keys.py`
**Purpose**: Adds missing translation keys to all language files based on the English template.

**Usage**:
```bash
python docs/scripts/maintenance/add_missing_translation_keys.py
```

**What it does**:
1. Reads the English translation file as reference
2. Compares each language file to find missing keys
3. Adds missing keys with placeholder translations
4. Maintains JSON structure and formatting

---

### `fix_satisfaction_translations.py`
**Purpose**: Fixes satisfaction survey translation structure across all language files.

**Usage**:
```bash
python docs/scripts/maintenance/fix_satisfaction_translations.py
```

**What it does**:
1. Converts flat satisfaction keys to nested JSON structure
2. Updates satisfaction survey translations
3. Ensures consistency across all language files

---

### `extract_translation_keys.py`
**Purpose**: Extracts all translation keys from the English translation file.

**Usage**:
```bash
python docs/scripts/maintenance/extract_translation_keys.py
```

**Output**: Creates `translation_keys.txt` with all keys (one per line).

**Use case**: Useful for auditing translation completeness or generating reports.

---

## Code Refactoring Scripts

### `rename_ai_service_to_rag.py`
**Purpose**: Renames references from "AI Service" to "RAG Service" across the codebase.

**Usage**:
```bash
python docs/scripts/maintenance/rename_ai_service_to_rag.py
```

**Scope**: Searches and replaces in:
- Backend Python files
- Frontend TypeScript/JavaScript files
- Configuration files

**What it does**:
1. Searches for "AI Service", "ai-service", "AI_SERVICE" patterns
2. Replaces with corresponding "RAG Service" variants
3. Reports all changes made
4. Skips binary files and node_modules

**Note**: Always review changes before committing.

---

## Best Practices

### Before Running Scripts
1. **Backup**: Ensure you have a clean git state or backup
2. **Review**: Read the script to understand what it will modify
3. **Test**: Run on a single file first if possible

### After Running Scripts
1. **Verify**: Check the changes made by the script
2. **Test**: Run relevant tests (e.g., `npm run build` for frontend)
3. **Commit**: Commit changes with descriptive message
4. **Update i18n**: If modifying translations, always run `update_i18n_interface.py` after

### Translation Workflow
When adding new translation keys:

1. Add keys to `frontend/public/locales/en.json` (English reference)
2. Create or modify a script to add translations to all 16 languages
3. Run the script to update all language files
4. Run `update_i18n_interface.py` to regenerate TypeScript interface
5. Run `npm run build` in frontend to verify compilation
6. Commit all changes together

### Script Development Guidelines
- Use Python 3.8+ for compatibility
- Handle encoding properly (UTF-8)
- Include error handling for file operations
- Print clear progress messages
- Use the pattern `[OK]` for Windows console compatibility (avoid emojis)
- Include docstrings explaining purpose and usage

---

## Troubleshooting

### "UnicodeEncodeError" on Windows
**Solution**: Replace emoji/special characters with ASCII text like `[OK]`, `[ERROR]`

### Translation keys not found in TypeScript
**Solution**: Run `update_i18n_interface.py` to regenerate the interface

### JSON syntax errors after script execution
**Solution**: Use a JSON validator or `python -m json.tool <file>` to check syntax

### Script doesn't find files
**Solution**: Ensure you're running from the project root directory

---

## Version History

- **2025-10-28**: Initial maintenance scripts documentation
  - Translation management scripts
  - Code refactoring utilities
  - Best practices guide
