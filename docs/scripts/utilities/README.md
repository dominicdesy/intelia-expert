# Utility Scripts

**Purpose:** General-purpose utility scripts for translations, versioning, and project maintenance.

## Translation Scripts

### Voice Feature Translations
- **`add_voice_translations.py`** - Add voice feature translations across all 16 languages
- **`add_voice_assistant_help_translations.py`** - Add voice assistant help text translations
- **`add_voice_speed_translations.py`** - Add voice speed control translations
- **`add_voice_descriptions_backend.py`** - Add voice descriptions to backend

### Widget & UI Translations
- **`add_widget_translations.py`** - Add widget-related translations
- **`add-cot-translations.js`** - Add Chain-of-Thought (CoT) translations

### Translation Management
- **`copy_translations_to_all_langs.py`** - Copy translation keys across all languages
- **`fix_missing_translations.py`** - Fix missing translation keys
- **`flatten_all_nested.py`** - Flatten all nested translation structures
- **`flatten_common.py`** - Flatten common translation keys
- **`flatten_voice_settings.py`** - Flatten voice settings translations
- **`check_translations.js`** - Validate translation file integrity

### Hardcoded Text Replacement
- **`replace_hardcoded_text.py`** - Replace hardcoded text with i18n keys
- **`replace_country_pricing.py`** - Replace country-specific pricing text

## Versioning & Documentation

- **`add_version_headers.py`** - Add version headers to source files
- **`generate_licenses.py`** - Generate license files for dependencies

## Security & Compliance

- **`verify-hsts-preload.sh`** - Verify HSTS preload configuration for security

## Usage

All scripts are executable and can be run from the project root:

```bash
# Example: Add voice translations
python docs/scripts/utilities/add_voice_translations.py

# Example: Verify HSTS preload
bash docs/scripts/utilities/verify-hsts-preload.sh
```

## Notes

- Most scripts are for one-time or occasional use
- Translation scripts should be run after adding new features with user-facing text
- Version header script is useful before major releases
- License generation should be run when dependencies are updated
