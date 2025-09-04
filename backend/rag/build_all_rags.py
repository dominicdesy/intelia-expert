#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-RAG Index Builder
Builds broiler, layer, and global RAG indexes in sequence or parallel
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess
import concurrent.futures
from dataclasses import dataclass
import json

# ----------------------------- Configuration --------------------------------

@dataclass
class RAGConfig:
    species: str
    src_path: str
    description: str
    exts: str = ".pdf,.txt,.md,.html,.htm,.csv,.xlsx,.xls"
    pdf_providers: str = "pdftotext,pymupdf,pypdfium2"
    chunk_size: int = 2000
    enable_ocr: bool = False

# Default configurations
DEFAULT_CONFIGS = {
    "broiler": RAGConfig(
        species="broiler",
        src_path="documents/public/species/broiler",
        description="Broiler chicken documentation and performance data"
    ),
    "layer": RAGConfig(
        species="layer", 
        src_path="documents/public/species/layer",
        description="Layer chicken documentation and performance data"
    ),
    "global": RAGConfig(
        species="global",
        src_path="documents/public",
        description="All species documentation (global index)"
    )
}

# ----------------------------- Logging ---------------------------------

def log(msg: str, prefix: str = "") -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {prefix}{msg}", flush=True)

def log_success(msg: str) -> None:
    log(f"✅ {msg}", "SUCCESS: ")

def log_error(msg: str) -> None:
    log(f"❌ {msg}", "ERROR: ")

def log_info(msg: str) -> None:
    log(f"ℹ️  {msg}", "INFO: ")

def log_warning(msg: str) -> None:
    log(f"⚠️  {msg}", "WARNING: ")

# ----------------------------- Build Functions -------------------------

def build_single_rag(
    config: RAGConfig,
    base_path: Path,
    output_path: Path,
    embeddings: str = "openai",
    embed_model: str = "text-embedding-3-small",
    verbose: bool = True,
    enhanced_metadata: bool = True,
    enable_quality_filter: bool = True,
    timeout: int = 300,
    additional_args: List[str] = None
) -> Dict[str, Any]:
    """
    Build a single RAG index
    Returns dict with status, timing, and stats
    """
    start_time = time.time()
    src_full = base_path / config.src_path
    
    if not src_full.exists():
        return {
            "species": config.species,
            "status": "error",
            "error": f"Source path not found: {src_full}",
            "duration": 0
        }

    # Find build_rag.py in the same directory as this script
    build_rag_path = Path(__file__).parent / "build_rag.py"
    if not build_rag_path.exists():
        # Fallback: try current directory
        build_rag_path = Path("build_rag.py")
        if not build_rag_path.exists():
            return {
                "species": config.species,
                "status": "error",
                "error": f"build_rag.py not found in {Path(__file__).parent} or current directory",
                "duration": 0
            }

    # Build command using direct script path
    cmd = [
        sys.executable, str(build_rag_path),
        "--src", str(src_full),
        "--out", str(output_path),
        "--species", config.species,
        "--embeddings", embeddings,
        "--embed-model", embed_model,
        "--exts", config.exts,
        "--pdf-providers", config.pdf_providers,
        "--chunk-size", str(config.chunk_size)
    ]
    
    # Add optional flags
    if enhanced_metadata:
        cmd.append("--enhanced-metadata")
    if enable_quality_filter:
        cmd.append("--enable-quality-filter")
    if verbose:
        cmd.append("--verbose")
    if config.enable_ocr:
        cmd.extend(["--enable-ocr", "--ocr-dpi", "220"])
    
    # Add any additional arguments
    if additional_args:
        cmd.extend(additional_args)

    log_info(f"Starting {config.species} RAG build...")
    log_info(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            # Parse output for statistics
            output_lines = result.stdout.split('\n')
            stats = extract_stats_from_output(output_lines)
            
            log_success(f"{config.species} RAG completed in {duration:.1f}s")
            return {
                "species": config.species,
                "status": "success",
                "duration": duration,
                "stats": stats,
                "output": result.stdout
            }
        else:
            log_error(f"{config.species} RAG failed (exit code {result.returncode})")
            if verbose:
                log_error(f"Error output: {result.stderr}")
            return {
                "species": config.species,
                "status": "error",
                "error": result.stderr,
                "duration": duration,
                "output": result.stdout
            }
    
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        log_error(f"{config.species} RAG timed out after {timeout}s")
        return {
            "species": config.species,
            "status": "timeout",
            "error": f"Build timed out after {timeout}s",
            "duration": duration
        }
    
    except Exception as e:
        duration = time.time() - start_time
        log_error(f"{config.species} RAG failed with exception: {e}")
        return {
            "species": config.species,
            "status": "error", 
            "error": str(e),
            "duration": duration
        }

def extract_stats_from_output(lines: List[str]) -> Dict[str, Any]:
    """Extract statistics from build output"""
    stats = {}
    for line in lines:
        line = line.strip()
        if "Total files detected:" in line:
            try:
                stats["total_files"] = int(line.split(":")[-1].strip())
            except ValueError:
                pass
        elif "Total chunks indexed:" in line:
            try:
                stats["total_chunks"] = int(line.split(":")[-1].strip())
            except ValueError:
                pass
        elif "CSV files processed:" in line:
            try:
                stats["csv_files"] = int(line.split(":")[-1].strip())
            except ValueError:
                pass
        elif "Performance tables:" in line:
            try:
                stats["perf_tables"] = int(line.split(":")[-1].strip())
            except ValueError:
                pass
        elif "Embedding dimensions:" in line:
            try:
                stats["embedding_dim"] = int(line.split(":")[-1].strip())
            except ValueError:
                pass
    return stats

def build_all_rags_sequential(
    configs: Dict[str, RAGConfig],
    base_path: Path,
    output_path: Path,
    **kwargs
) -> List[Dict[str, Any]]:
    """Build all RAG indexes sequentially"""
    results = []
    
    log_info(f"Building {len(configs)} RAG indexes sequentially...")
    for species, config in configs.items():
        log_info(f"\n{'='*60}")
        log_info(f"Building {species} RAG ({config.description})")
        log_info(f"{'='*60}")
        
        result = build_single_rag(config, base_path, output_path, **kwargs)
        results.append(result)
        
        if result["status"] == "success":
            log_success(f"{species} completed in {result['duration']:.1f}s")
            if "stats" in result:
                stats = result["stats"]
                log_info(f"  Files: {stats.get('total_files', 'N/A')}")
                log_info(f"  Chunks: {stats.get('total_chunks', 'N/A')}")
                log_info(f"  CSV files: {stats.get('csv_files', 'N/A')}")
        else:
            log_error(f"{species} failed: {result.get('error', 'Unknown error')}")
    
    return results

def build_all_rags_parallel(
    configs: Dict[str, RAGConfig],
    base_path: Path,
    output_path: Path,
    max_workers: int = 2,
    **kwargs
) -> List[Dict[str, Any]]:
    """Build all RAG indexes in parallel"""
    log_info(f"Building {len(configs)} RAG indexes in parallel (max_workers={max_workers})...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all jobs
        futures = {}
        for species, config in configs.items():
            log_info(f"Submitting {species} RAG build...")
            future = executor.submit(build_single_rag, config, base_path, output_path, **kwargs)
            futures[future] = species
        
        # Collect results
        results = []
        for future in concurrent.futures.as_completed(futures):
            species = futures[future]
            try:
                result = future.result()
                results.append(result)
                
                if result["status"] == "success":
                    log_success(f"{species} completed in {result['duration']:.1f}s")
                else:
                    log_error(f"{species} failed: {result.get('error', 'Unknown error')}")
            except Exception as e:
                log_error(f"{species} raised exception: {e}")
                results.append({
                    "species": species,
                    "status": "error",
                    "error": str(e),
                    "duration": 0
                })
    
    return results

def save_build_report(results: List[Dict[str, Any]], output_path: Path) -> None:
    """Save build report as JSON"""
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_builds": len(results),
        "successful_builds": sum(1 for r in results if r["status"] == "success"),
        "failed_builds": sum(1 for r in results if r["status"] != "success"),
        "total_duration": sum(r.get("duration", 0) for r in results),
        "results": results
    }
    
    report_path = output_path / "build_report.json"
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        log_success(f"Build report saved: {report_path}")
    except Exception as e:
        log_error(f"Failed to save build report: {e}")

# ----------------------------- CLI Interface ---------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Build multiple RAG indexes (broiler, layer, global)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build all three indexes sequentially
  python build_all_rags.py --base-path /path/to/intelia_gpt --out /path/to/rag_index
  
  # Build only broiler and layer in parallel
  python build_all_rags.py --indexes broiler,layer --parallel --max-workers 2
  
  # Custom embedding settings
  python build_all_rags.py --embeddings fastembed --embed-model BAAI/bge-small-en-v1.5
  
  # Enable OCR for broiler only
  python build_all_rags.py --indexes broiler --enable-ocr
        """
    )
    
    # Required paths
    parser.add_argument("--base-path", type=Path, default=Path.cwd(),
                       help="Base path containing documents/ folder (default: current directory)")
    parser.add_argument("--out", type=Path, required=True,
                       help="Output directory for RAG indexes")
    
    # Index selection
    parser.add_argument("--indexes", default="broiler,layer,global",
                       help="Comma-separated list of indexes to build (default: broiler,layer,global)")
    
    # Build options
    parser.add_argument("--parallel", action="store_true",
                       help="Build indexes in parallel instead of sequential")
    parser.add_argument("--max-workers", type=int, default=2,
                       help="Max parallel workers when using --parallel (default: 2)")
    
    # Embedding options
    parser.add_argument("--embeddings", choices=["openai", "fastembed", "sentencetransformers"], 
                       default="openai", help="Embedding provider")
    parser.add_argument("--embed-model", default="text-embedding-3-small",
                       help="Embedding model name")
    
    # Processing options
    parser.add_argument("--no-enhanced-metadata", action="store_true",
                       help="Disable enhanced metadata enrichment")
    parser.add_argument("--no-quality-filter", action="store_true", 
                       help="Disable quality filtering")
    parser.add_argument("--enable-ocr", action="store_true",
                       help="Enable OCR for all indexes")
    parser.add_argument("--timeout", type=int, default=600,
                       help="Timeout per index build in seconds (default: 600)")
    
    # Output options
    parser.add_argument("--quiet", action="store_true",
                       help="Reduce output verbosity")
    parser.add_argument("--save-report", action="store_true", default=True,
                       help="Save build report as JSON (default: True)")
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Validate paths
    if not args.base_path.exists():
        log_error(f"Base path does not exist: {args.base_path}")
        return 1
    
    documents_path = args.base_path / "documents"
    if not documents_path.exists():
        log_error(f"Documents folder not found: {documents_path}")
        return 1
    
    # Create output directory
    args.out.mkdir(parents=True, exist_ok=True)
    
    # Parse requested indexes
    requested_indexes = [idx.strip() for idx in args.indexes.split(",")]
    configs = {}
    for idx in requested_indexes:
        if idx in DEFAULT_CONFIGS:
            configs[idx] = DEFAULT_CONFIGS[idx]
        else:
            log_warning(f"Unknown index type: {idx}")
    
    if not configs:
        log_error("No valid indexes specified")
        return 1
    
    log_info(f"Multi-RAG Index Builder")
    log_info(f"Base path: {args.base_path}")
    log_info(f"Output path: {args.out}")
    log_info(f"Indexes to build: {list(configs.keys())}")
    log_info(f"Embedding provider: {args.embeddings}")
    log_info(f"Parallel: {'Yes' if args.parallel else 'No'}")
    if args.parallel:
        log_info(f"Max workers: {args.max_workers}")
    
    # Build parameters
    build_params = {
        "embeddings": args.embeddings,
        "embed_model": args.embed_model,
        "verbose": not args.quiet,
        "enhanced_metadata": not args.no_enhanced_metadata,
        "enable_quality_filter": not args.no_quality_filter,
        "timeout": args.timeout
    }
    
    # Enable OCR for all if requested
    if args.enable_ocr:
        for config in configs.values():
            config.enable_ocr = True
    
    # Build indexes
    start_time = time.time()
    
    if args.parallel:
        results = build_all_rags_parallel(
            configs, args.base_path, args.out, 
            max_workers=args.max_workers,
            **build_params
        )
    else:
        results = build_all_rags_sequential(
            configs, args.base_path, args.out,
            **build_params
        )
    
    total_duration = time.time() - start_time
    
    # Summary
    successful = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - successful
    
    log_info(f"\n{'='*60}")
    log_info(f"MULTI-RAG BUILD COMPLETE")
    log_info(f"{'='*60}")
    log_info(f"Total time: {total_duration:.1f}s")
    log_info(f"Successful builds: {successful}/{len(results)}")
    log_info(f"Failed builds: {failed}/{len(results)}")
    
    # Show individual results
    for result in results:
        species = result["species"]
        status = result["status"]
        duration = result.get("duration", 0)
        
        if status == "success":
            log_success(f"{species}: {duration:.1f}s")
            if "stats" in result:
                stats = result["stats"]
                log_info(f"  └─ Files: {stats.get('total_files', '?')}, "
                        f"Chunks: {stats.get('total_chunks', '?')}, "
                        f"CSV: {stats.get('csv_files', '?')}")
        else:
            log_error(f"{species}: {status} ({duration:.1f}s)")
            if "error" in result:
                log_error(f"  └─ {result['error']}")
    
    # Save report
    if args.save_report:
        save_build_report(results, args.out)
    
    # Return appropriate exit code
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
