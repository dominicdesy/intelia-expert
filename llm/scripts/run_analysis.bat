@echo off
REM Ultra-Complete LLM Analysis - Run all analysis scripts
REM This will run overnight to analyze the entire codebase

echo ================================================================================
echo LLM OPTIMIZATION ANALYSIS - Starting Complete Analysis
echo ================================================================================
echo.

cd /d "%~dp0.."

echo [%TIME%] Starting codebase analysis (unused files, dead code)...
python scripts/analyze_unused_files.py > logs/codebase_analysis_output.log 2>&1

echo [%TIME%] Starting deep optimization analysis (complexity, performance)...
python scripts/deep_optimization_analysis.py > logs/deep_optimization_output.log 2>&1

echo.
echo ================================================================================
echo Analysis Complete!
echo ================================================================================
echo.
echo Reports generated:
echo   - logs/codebase_analysis_report.json
echo   - logs/deep_optimization_report.json
echo.
echo View results with: python scripts/view_analysis_results.py
echo.

pause
