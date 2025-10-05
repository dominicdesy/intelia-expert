#!/bin/bash
# Duplicate code analysis script for LLM module

echo "==================================================================="
echo "DUPLICATE CODE ANALYSIS - LLM Module"
echo "==================================================================="
echo ""

# Method 1: Simple pattern detection with grep
echo "1. SEARCHING FOR DUPLICATE FUNCTION SIGNATURES..."
echo "-------------------------------------------------------------------"
grep -r "^def\|^async def" --include="*.py" . | \
  awk -F: '{print $2}' | \
  sort | \
  uniq -c | \
  sort -rn | \
  awk '$1 > 1 {print $1 " occurrences: " substr($0, index($0,$2))}'
echo ""

# Method 2: Find similar class definitions
echo "2. SEARCHING FOR DUPLICATE CLASS NAMES..."
echo "-------------------------------------------------------------------"
grep -r "^class " --include="*.py" . | \
  awk -F: '{print $2}' | \
  sort | \
  uniq -c | \
  sort -rn | \
  awk '$1 > 1 {print $1 " occurrences: " substr($0, index($0,$2))}'
echo ""

# Method 3: Find files with similar patterns
echo "3. FILES WITH MOST SIMILAR PATTERNS (by line count)..."
echo "-------------------------------------------------------------------"
find . -name "*.py" -type f -exec wc -l {} + | \
  sort -rn | \
  head -20 | \
  awk '{print $1 " lines: " $2}'
echo ""

# Method 4: Search for common code smells
echo "4. POTENTIAL CODE DUPLICATION INDICATORS..."
echo "-------------------------------------------------------------------"
echo "A. Similar try/except blocks:"
grep -r "try:" --include="*.py" . | wc -l | awk '{print "   Total try blocks: " $1}'

echo "B. Similar logging patterns:"
grep -r "logger\." --include="*.py" . | \
  awk -F: '{print $2}' | \
  sed 's/.*logger\.\([a-z]*\).*/\1/' | \
  sort | \
  uniq -c | \
  sort -rn | \
  head -5

echo "C. Files with TODO/FIXME comments:"
grep -r "TODO\|FIXME\|XXX" --include="*.py" . | wc -l | awk '{print "   Total: " $1}'
echo ""

# Method 5: Similar import patterns
echo "5. MOST COMMON IMPORTS (potential for consolidation)..."
echo "-------------------------------------------------------------------"
grep -r "^from\|^import" --include="*.py" . | \
  awk -F: '{print $2}' | \
  sort | \
  uniq -c | \
  sort -rn | \
  head -10
echo ""

echo "==================================================================="
echo "ANALYSIS COMPLETE"
echo "==================================================================="
