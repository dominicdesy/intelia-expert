#!/usr/bin/env python3
"""
Migration Script: Old Structure → New Simplified Structure
===========================================================

This script maps the 50 existing PDFs from the old Species-First structure
to the new Simplified Structure with horizontal services.

OLD STRUCTURE (Species-First):
  public/
    ├── common/health/
    └── species/
        ├── broiler/
        │   ├── breeds/
        │   ├── health/
        │   ├── housing/
        │   └── value_chain/
        └── layer/
            └── breeds/

NEW STRUCTURE (Simplified with Horizontal Services):
  Sources/intelia/public/
    ├── nutrition/
    ├── health/
    ├── veterinary_services/
    ├── breeding_farms/
    ├── hatcheries/
    ├── broiler_farms/
    ├── layer_farms/
    └── [other site types...]

Author: Claude Code
Date: 2025-10-29
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import json


class PDFMigrationMapper:
    """Maps PDFs from old structure to new simplified structure"""

    def __init__(self, base_old: str, base_new: str):
        self.base_old = Path(base_old)
        self.base_new = Path(base_new)
        self.migration_plan: List[Dict] = []

    def analyze_pdf(self, old_path: Path) -> Dict:
        """Analyze a PDF and determine its new location"""

        # Extract relative path from base
        rel_path = old_path.relative_to(self.base_old)
        parts = rel_path.parts

        filename = old_path.name

        # Initialize analysis
        analysis = {
            "old_path": str(old_path),
            "old_relative": str(rel_path),
            "filename": filename,
            "parts": parts,
            "new_path": None,
            "reasoning": [],
            "metadata": {}
        }

        # Determine new path based on analysis
        new_path = self._determine_new_path(parts, filename, analysis)
        analysis["new_path"] = str(new_path)

        return analysis

    def _determine_new_path(self, parts: Tuple, filename: str, analysis: Dict) -> Path:
        """Determine the new path based on file analysis"""

        # Base for all Intelia public documents
        base = self.base_new / "intelia" / "public"

        # ===================================================================
        # COMMON/HEALTH → health/common/
        # ===================================================================
        if "common" in parts and "health" in parts:
            analysis["reasoning"].append("Multi-species health document")
            analysis["metadata"]["species"] = ["broiler", "layer", "breeder", "turkey"]
            analysis["metadata"]["site_type"] = ["breeding_farms", "broiler_farms", "layer_farms"]

            # Classify by disease type or topic
            fn_lower = filename.lower()

            # Disease-specific categories
            if any(x in fn_lower for x in ["coccidiosis", "coccidia"]):
                new_path = base / "health" / "common" / "diseases" / "parasitic"
                analysis["metadata"]["category_level2"] = "Disease_Management"
                analysis["metadata"]["disease_type"] = "parasitic"

            elif any(x in fn_lower for x in ["ibd", "infectious_bursal", "bursal"]):
                new_path = base / "health" / "common" / "diseases" / "viral"
                analysis["metadata"]["category_level2"] = "Disease_Management"
                analysis["metadata"]["disease_type"] = "viral"

            elif any(x in fn_lower for x in ["ilt", "infectious_laryngo"]):
                new_path = base / "health" / "common" / "diseases" / "viral"
                analysis["metadata"]["category_level2"] = "Disease_Management"
                analysis["metadata"]["disease_type"] = "viral"

            elif any(x in fn_lower for x in ["ibv", "infectious_bronchitis", "bronchitis"]):
                new_path = base / "health" / "common" / "diseases" / "viral"
                analysis["metadata"]["category_level2"] = "Disease_Management"
                analysis["metadata"]["disease_type"] = "viral"

            elif any(x in fn_lower for x in ["cholera", "fowl_cholera"]):
                new_path = base / "health" / "common" / "diseases" / "bacterial"
                analysis["metadata"]["category_level2"] = "Disease_Management"
                analysis["metadata"]["disease_type"] = "bacterial"

            elif any(x in fn_lower for x in ["staph", "staphylococcus"]):
                new_path = base / "health" / "common" / "diseases" / "bacterial"
                analysis["metadata"]["category_level2"] = "Disease_Management"
                analysis["metadata"]["disease_type"] = "bacterial"

            elif any(x in fn_lower for x in ["myco", "mycoplasma"]):
                new_path = base / "health" / "common" / "diseases" / "bacterial"
                analysis["metadata"]["category_level2"] = "Disease_Management"
                analysis["metadata"]["disease_type"] = "bacterial"

            elif any(x in fn_lower for x in ["ascites", "pulmonary"]):
                new_path = base / "health" / "common" / "diseases" / "metabolic"
                analysis["metadata"]["category_level2"] = "Disease_Management"
                analysis["metadata"]["disease_type"] = "metabolic"

            elif any(x in fn_lower for x in ["pectoral", "myopathy"]):
                new_path = base / "health" / "common" / "diseases" / "metabolic"
                analysis["metadata"]["category_level2"] = "Disease_Management"
                analysis["metadata"]["disease_type"] = "metabolic"

            # Management topics
            elif any(x in fn_lower for x in ["water", "drinking"]):
                new_path = base / "health" / "common" / "management" / "water_quality"
                analysis["metadata"]["category_level2"] = "Health_Management"

            elif any(x in fn_lower for x in ["heat", "stress"]):
                new_path = base / "health" / "common" / "management" / "stress_management"
                analysis["metadata"]["category_level2"] = "Health_Management"

            elif any(x in fn_lower for x in ["beak", "management"]):
                new_path = base / "health" / "common" / "management" / "welfare"
                analysis["metadata"]["category_level2"] = "Health_Management"

            elif any(x in fn_lower for x in ["nest", "nesting"]):
                new_path = base / "layer_farms" / "common" / "management" / "laying_management"
                analysis["metadata"]["category_level2"] = "Production_Management"
                analysis["metadata"]["site_type"] = ["layer_farms"]

            elif any(x in fn_lower for x in ["fly", "flies"]):
                new_path = base / "health" / "common" / "biosecurity" / "pest_control"
                analysis["metadata"]["category_level2"] = "Biosecurity"

            elif any(x in fn_lower for x in ["eds", "egg_drop"]):
                new_path = base / "health" / "common" / "diseases" / "viral"
                analysis["metadata"]["category_level2"] = "Disease_Management"
                analysis["metadata"]["disease_type"] = "viral"

            elif any(x in fn_lower for x in ["lpai", "avian_influenza"]):
                new_path = base / "health" / "common" / "diseases" / "viral"
                analysis["metadata"]["category_level2"] = "Disease_Management"
                analysis["metadata"]["disease_type"] = "viral"

            elif any(x in fn_lower for x in ["manual", "poultry_diseases"]):
                new_path = base / "health" / "common" / "reference_guides"
                analysis["metadata"]["category_level2"] = "Reference_Materials"

            elif any(x in fn_lower for x in ["col", "colibacillosis"]):
                new_path = base / "health" / "common" / "diseases" / "bacterial"
                analysis["metadata"]["category_level2"] = "Disease_Management"
                analysis["metadata"]["disease_type"] = "bacterial"

            elif any(x in fn_lower for x in ["scratches", "skin"]):
                new_path = base / "health" / "common" / "diseases" / "physical_conditions"
                analysis["metadata"]["category_level2"] = "Health_Conditions"

            else:
                # Default: common health
                new_path = base / "health" / "common" / "general"
                analysis["metadata"]["category_level2"] = "General_Health"

        # ===================================================================
        # BROILER SPECIFIC DOCUMENTS
        # ===================================================================
        elif "broiler" in parts:
            analysis["metadata"]["species"] = ["broiler"]

            # Biosecurity
            if "biosecurity" in parts or "biosec" in filename.lower():
                new_path = base / "broiler_farms" / "common" / "biosecurity"
                analysis["reasoning"].append("Broiler farm biosecurity")
                analysis["metadata"]["site_type"] = ["broiler_farms"]
                analysis["metadata"]["category_level2"] = "Biosecurity"

            # Breed-specific (Ross 308)
            elif "ross_308" in parts or "ross" in filename.lower():

                # Parent stock
                if "parentstock" in parts or "ps" in filename.lower() or "parent" in filename.lower():
                    analysis["reasoning"].append("Ross 308 parent stock")
                    analysis["metadata"]["breed"] = "Ross 308 PS"
                    analysis["metadata"]["site_type"] = ["breeding_farms"]

                    if "handbook" in filename.lower():
                        new_path = base / "breeding_farms" / "by_breed" / "ross_308_ps" / "management"
                        analysis["metadata"]["category_level2"] = "Management_Guide"
                    else:
                        new_path = base / "breeding_farms" / "by_breed" / "ross_308_ps" / "general"

                # Commercial broilers
                else:
                    analysis["reasoning"].append("Ross 308 commercial broilers")
                    analysis["metadata"]["breed"] = "Ross 308"
                    analysis["metadata"]["site_type"] = ["broiler_farms"]

                    if "handbook" in filename.lower():
                        new_path = base / "broiler_farms" / "by_breed" / "ross_308" / "management"
                        analysis["metadata"]["category_level2"] = "Management_Guide"

                    elif "nutrition" in filename.lower():
                        new_path = base / "nutrition" / "broiler" / "by_breed" / "ross_308" / "specifications"
                        analysis["metadata"]["category_level2"] = "Nutrition_Specifications"

                    elif "performance" in filename.lower():
                        new_path = base / "broiler_farms" / "by_breed" / "ross_308" / "performance_standards"
                        analysis["metadata"]["category_level2"] = "Performance_Standards"

                    elif "management" in filename.lower() or "mgt" in filename.lower():
                        new_path = base / "broiler_farms" / "by_breed" / "ross_308" / "management"
                        analysis["metadata"]["category_level2"] = "Management_Guide"

                    else:
                        new_path = base / "broiler_farms" / "by_breed" / "ross_308" / "general"

            # Breed-specific (Cobb 500)
            elif "cobb" in parts or "cobb" in filename.lower():

                # Breeder
                if "breeder" in filename.lower() and "management" in filename.lower():
                    analysis["reasoning"].append("Cobb 500 breeder management")
                    analysis["metadata"]["breed"] = "Cobb 500 Breeder"
                    analysis["metadata"]["site_type"] = ["breeding_farms"]
                    new_path = base / "breeding_farms" / "by_breed" / "cobb_500_breeder" / "management"
                    analysis["metadata"]["category_level2"] = "Management_Guide"

                # Fast/Slow feather breeder supplements
                elif any(x in filename.lower() for x in ["fast-feather", "slow-feather"]):
                    analysis["reasoning"].append("Cobb 500 breeder feathering supplement")
                    analysis["metadata"]["breed"] = "Cobb 500 Breeder"
                    analysis["metadata"]["site_type"] = ["breeding_farms"]
                    new_path = base / "breeding_farms" / "by_breed" / "cobb_500_breeder" / "management"
                    analysis["metadata"]["category_level2"] = "Management_Supplement"

                # Male supplements
                elif "male" in filename.lower():
                    analysis["reasoning"].append("Cobb breeder male management")
                    analysis["metadata"]["breed"] = "Cobb Breeder"
                    analysis["metadata"]["site_type"] = ["breeding_farms"]
                    new_path = base / "breeding_farms" / "by_breed" / "cobb_500_breeder" / "management"
                    analysis["metadata"]["category_level2"] = "Management_Supplement"

                # Post-mortem guide
                elif "post-mortem" in filename.lower():
                    analysis["reasoning"].append("Cobb breeder health diagnostic guide")
                    analysis["metadata"]["breed"] = "Cobb Breeder"
                    analysis["metadata"]["site_type"] = ["breeding_farms"]
                    new_path = base / "veterinary_services" / "diagnostics" / "post_mortem_guides" / "breeders"
                    analysis["metadata"]["category_level2"] = "Diagnostic_Guide"

                # Commercial broilers
                else:
                    analysis["reasoning"].append("Cobb 500 commercial broilers")
                    analysis["metadata"]["breed"] = "Cobb 500"
                    analysis["metadata"]["site_type"] = ["broiler_farms"]

                    if "guide" in filename.lower() and "broiler" in filename.lower():
                        new_path = base / "broiler_farms" / "by_breed" / "cobb_500" / "management"
                        analysis["metadata"]["category_level2"] = "Management_Guide"

                    elif "nutrition" in filename.lower():
                        new_path = base / "nutrition" / "broiler" / "by_breed" / "cobb_500" / "specifications"
                        analysis["metadata"]["category_level2"] = "Nutrition_Specifications"

                    elif "performance" in filename.lower():
                        new_path = base / "broiler_farms" / "by_breed" / "cobb_500" / "performance_standards"
                        analysis["metadata"]["category_level2"] = "Performance_Standards"

                    else:
                        new_path = base / "broiler_farms" / "by_breed" / "cobb_500" / "general"

            # Broiler health (species-specific)
            elif "health" in parts or "gut-health" in filename.lower():
                analysis["reasoning"].append("Broiler-specific health management")
                analysis["metadata"]["site_type"] = ["broiler_farms"]
                new_path = base / "health" / "broiler" / "common" / "gut_health"
                analysis["metadata"]["category_level2"] = "Health_Management"

            # Broiler housing
            elif "housing" in parts or "housing" in filename.lower():
                analysis["reasoning"].append("Broiler housing and environment")
                analysis["metadata"]["site_type"] = ["broiler_farms"]

                if "optimum" in filename.lower() and "development" in filename.lower():
                    new_path = base / "broiler_farms" / "common" / "housing" / "environmental_management"
                    analysis["metadata"]["category_level2"] = "Housing_Environment"
                else:
                    new_path = base / "broiler_farms" / "common" / "housing" / "general"

            # Value chain documents
            elif "value_chain" in parts or "hatchery" in filename.lower():
                analysis["reasoning"].append("Broiler value chain operations")

                if "hatchery" in filename.lower():
                    analysis["metadata"]["site_type"] = ["hatcheries"]
                    new_path = base / "hatcheries" / "broiler" / "common" / "operations"
                    analysis["metadata"]["category_level2"] = "Hatchery_Operations"

                else:
                    # Generic processing/value chain
                    analysis["metadata"]["site_type"] = ["processing_plants"]
                    new_path = base / "processing_plants" / "broiler" / "common" / "operations"
                    analysis["metadata"]["category_level2"] = "Processing_Operations"

            else:
                # Default broiler
                new_path = base / "broiler_farms" / "common" / "general"
                analysis["metadata"]["site_type"] = ["broiler_farms"]

        # ===================================================================
        # LAYER SPECIFIC DOCUMENTS
        # ===================================================================
        elif "layer" in parts:
            analysis["metadata"]["species"] = ["layer"]
            analysis["metadata"]["site_type"] = ["layer_farms"]

            # Hy-Line Brown
            if "hy_line_brown" in parts or "hyline_brown" in filename.lower() or "hyline brown" in filename.lower():
                analysis["reasoning"].append("Hy-Line Brown layers")
                analysis["metadata"]["breed"] = "Hy-Line Brown"

                if "parent" in filename.lower() or "ps" in filename.lower():
                    analysis["metadata"]["site_type"] = ["breeding_farms"]
                    new_path = base / "breeding_farms" / "by_breed" / "hy_line_brown_ps" / "performance_standards"
                    analysis["metadata"]["category_level2"] = "Performance_Standards"

                elif "alt" in filename.lower():
                    new_path = base / "layer_farms" / "by_breed" / "hy_line_brown" / "performance_standards"
                    analysis["metadata"]["category_level2"] = "Performance_Standards"
                    analysis["metadata"]["housing_system"] = "alternative"

                else:
                    new_path = base / "layer_farms" / "by_breed" / "hy_line_brown" / "performance_standards"
                    analysis["metadata"]["category_level2"] = "Performance_Standards"

            # Hy-Line W-36
            elif "hy_line_w_36" in parts or "w36" in filename.lower() or "w-36" in filename.lower():
                analysis["reasoning"].append("Hy-Line W-36 layers")
                analysis["metadata"]["breed"] = "Hy-Line W-36"

                if "parent" in filename.lower() or "ps" in filename.lower():
                    analysis["metadata"]["site_type"] = ["breeding_farms"]
                    new_path = base / "breeding_farms" / "by_breed" / "hy_line_w36_ps" / "performance_standards"
                    analysis["metadata"]["category_level2"] = "Performance_Standards"

                elif "conventional" in filename.lower() or "performance" in filename.lower():
                    new_path = base / "layer_farms" / "by_breed" / "hy_line_w36" / "performance_standards"
                    analysis["metadata"]["category_level2"] = "Performance_Standards"

                else:
                    new_path = base / "layer_farms" / "by_breed" / "hy_line_w36" / "performance_standards"
                    analysis["metadata"]["category_level2"] = "Performance_Standards"

            # Hy-Line W-80
            elif "hy_line_w_80" in parts or "w80" in filename.lower() or "w-80" in filename.lower():
                analysis["reasoning"].append("Hy-Line W-80 layers")
                analysis["metadata"]["breed"] = "Hy-Line W-80"

                if "parent" in filename.lower() or "ps" in filename.lower():
                    analysis["metadata"]["site_type"] = ["breeding_farms"]
                    new_path = base / "breeding_farms" / "by_breed" / "hy_line_w80_ps" / "performance_standards"
                    analysis["metadata"]["category_level2"] = "Performance_Standards"

                else:
                    new_path = base / "layer_farms" / "by_breed" / "hy_line_w80" / "performance_standards"
                    analysis["metadata"]["category_level2"] = "Performance_Standards"

            # Lohmann Brown
            elif "lohmann_brown" in parts or "lohmann-brown" in filename.lower():
                analysis["reasoning"].append("Lohmann Brown layers")
                analysis["metadata"]["breed"] = "Lohmann Brown Classic"
                new_path = base / "layer_farms" / "by_breed" / "lohmann_brown_classic" / "performance_standards"
                analysis["metadata"]["category_level2"] = "Performance_Standards"
                analysis["metadata"]["housing_system"] = "cage"

            # Lohmann LSL
            elif "lohmann_lsl" in parts or "lohmann-lsl" in filename.lower():
                analysis["reasoning"].append("Lohmann LSL layers")
                analysis["metadata"]["breed"] = "Lohmann LSL Lite"
                new_path = base / "layer_farms" / "by_breed" / "lohmann_lsl_lite" / "performance_standards"
                analysis["metadata"]["category_level2"] = "Performance_Standards"
                analysis["metadata"]["housing_system"] = "cage"

            else:
                # Default layer
                new_path = base / "layer_farms" / "common" / "general"

        else:
            # Fallback
            analysis["reasoning"].append("Unable to classify - needs manual review")
            new_path = base / "_to_review" / filename

        return new_path

    def generate_migration_plan(self, pdf_list: List[str]) -> None:
        """Generate complete migration plan for all PDFs"""

        print("=" * 80)
        print("MIGRATION PLAN GENERATION")
        print("=" * 80)
        print()

        for pdf_path_str in pdf_list:
            pdf_path = Path(pdf_path_str)

            if not pdf_path.exists():
                print(f"⚠ WARNING: File not found: {pdf_path}")
                continue

            analysis = self.analyze_pdf(pdf_path)
            self.migration_plan.append(analysis)

            print(f"✓ Analyzed: {analysis['filename']}")

        print()
        print(f"✅ Total files analyzed: {len(self.migration_plan)}")
        print()

    def export_migration_plan(self, output_path: str) -> None:
        """Export migration plan to JSON"""

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.migration_plan, f, indent=2, ensure_ascii=False)

        print(f"✅ Migration plan exported to: {output_path}")

    def generate_report(self, output_path: str) -> None:
        """Generate human-readable migration report"""

        report_lines = []

        report_lines.append("=" * 100)
        report_lines.append("MIGRATION REPORT: OLD STRUCTURE → NEW SIMPLIFIED STRUCTURE")
        report_lines.append("=" * 100)
        report_lines.append("")
        report_lines.append(f"Total PDFs analyzed: {len(self.migration_plan)}")
        report_lines.append("")
        report_lines.append("=" * 100)
        report_lines.append("DETAILED MIGRATION MAPPINGS")
        report_lines.append("=" * 100)
        report_lines.append("")

        for i, item in enumerate(self.migration_plan, 1):
            report_lines.append(f"{i}. {item['filename']}")
            report_lines.append(f"   {'─' * 90}")
            report_lines.append(f"   OLD: {item['old_relative']}")
            report_lines.append(f"   NEW: {Path(item['new_path']).relative_to(self.base_new)}")
            report_lines.append(f"   ")
            report_lines.append(f"   REASONING:")
            for reason in item['reasoning']:
                report_lines.append(f"     • {reason}")
            report_lines.append(f"   ")
            report_lines.append(f"   METADATA:")
            for key, value in item['metadata'].items():
                report_lines.append(f"     • {key}: {value}")
            report_lines.append("")

        report_lines.append("=" * 100)
        report_lines.append("DIRECTORY STRUCTURE SUMMARY")
        report_lines.append("=" * 100)
        report_lines.append("")

        # Count by top-level directory
        dir_counts = {}
        for item in self.migration_plan:
            new_path = Path(item['new_path'])
            rel_path = new_path.relative_to(self.base_new / "intelia" / "public")
            top_dir = rel_path.parts[0]
            dir_counts[top_dir] = dir_counts.get(top_dir, 0) + 1

        report_lines.append("Documents per top-level directory:")
        for dir_name, count in sorted(dir_counts.items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"  {dir_name:30} : {count:3} documents")

        report_lines.append("")
        report_lines.append("=" * 100)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 100)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        print(f"✅ Migration report exported to: {output_path}")

    def execute_migration(self, dry_run: bool = True) -> None:
        """Execute the actual file migration"""

        print()
        print("=" * 80)
        if dry_run:
            print("DRY RUN MODE - No files will be moved")
        else:
            print("EXECUTING MIGRATION - FILES WILL BE MOVED")
        print("=" * 80)
        print()

        moved_count = 0
        error_count = 0

        for item in self.migration_plan:
            old_path = Path(item['old_path'])
            new_path = Path(item['new_path'])

            if not old_path.exists():
                print(f"✗ ERROR: Source not found: {old_path}")
                error_count += 1
                continue

            if dry_run:
                print(f"[DRY RUN] Would move:")
                print(f"  FROM: {old_path}")
                print(f"  TO:   {new_path}")
                moved_count += 1
            else:
                # Create destination directory
                new_path.parent.mkdir(parents=True, exist_ok=True)

                # Move file
                try:
                    shutil.move(str(old_path), str(new_path))
                    print(f"✓ Moved: {item['filename']}")
                    moved_count += 1
                except Exception as e:
                    print(f"✗ ERROR moving {item['filename']}: {e}")
                    error_count += 1

        print()
        print("=" * 80)
        print(f"✅ Successfully processed: {moved_count}")
        if error_count > 0:
            print(f"✗ Errors: {error_count}")
        print("=" * 80)


def main():
    """Main execution"""

    # Paths
    OLD_BASE = "C:/Software_Development/documents/public"
    NEW_BASE = "C:/Software_Development/documents/Sources"

    # List of all 50 PDFs
    pdf_files = [
        "C:/Software_Development/documents/public/common/health/ascites.pdf",
        "C:/Software_Development/documents/public/common/health/AviaTech_Staph.pdf",
        "C:/Software_Development/documents/public/common/health/COCCIDIOSIS_CONTROL_Ken_Bafundo.pdf",
        "C:/Software_Development/documents/public/common/health/Deep-Pectoral-Myopathy-Canadian-Poultry-Consultants-20120809.pdf",
        "C:/Software_Development/documents/public/common/health/Drinking-Water-Management.pdf",
        "C:/Software_Development/documents/public/common/health/fowl_cholera.pdf",
        "C:/Software_Development/documents/public/common/health/ilt.pdf",
        "C:/Software_Development/documents/public/common/health/infectious_bronchitis_virus_ibv.pdf",
        "C:/Software_Development/documents/public/common/health/infectious_bursal_disease.pdf",
        "C:/Software_Development/documents/public/common/health/is2014.pdf",
        "C:/Software_Development/documents/public/common/health/Manual_of_poultry_diseases_en.pdf",
        "C:/Software_Development/documents/public/common/health/skin_scratches.pdf",
        "C:/Software_Development/documents/public/common/health/TU COL ENG.pdf",
        "C:/Software_Development/documents/public/common/health/TU EDS ENG.pdf",
        "C:/Software_Development/documents/public/common/health/TU FLY ENG.pdf",
        "C:/Software_Development/documents/public/common/health/TU Full beak management ENG.pdf",
        "C:/Software_Development/documents/public/common/health/TU HEAT ENG.pdf",
        "C:/Software_Development/documents/public/common/health/TU IBD ENG.pdf",
        "C:/Software_Development/documents/public/common/health/TU LPAI ENG.pdf",
        "C:/Software_Development/documents/public/common/health/TU MYCO ENG.pdf",
        "C:/Software_Development/documents/public/common/health/TU NEST ENG.pdf",
        "C:/Software_Development/documents/public/common/health/understandingcoccidiosis.pdf",
        "C:/Software_Development/documents/public/species/broiler/biosecurity/biosec-poultry-farms.pdf",
        "C:/Software_Development/documents/public/species/broiler/breeds/cobb/2022-Cobb500-Broiler-Performance-Nutrition-Supplement.pdf",
        "C:/Software_Development/documents/public/species/broiler/breeds/cobb/Breeder-Management-Guide.pdf",
        "C:/Software_Development/documents/public/species/broiler/breeds/cobb/Broiler-Guide_English-2021-min.pdf",
        "C:/Software_Development/documents/public/species/broiler/breeds/cobb/Cobb500-Fast-Feather-Breeder-Management-Supplement.pdf",
        "C:/Software_Development/documents/public/species/broiler/breeds/cobb/Cobb500-Slow-Feather-Breeder-Management-Supplement.pdf",
        "C:/Software_Development/documents/public/species/broiler/breeds/cobb/Cobb-Male-Supplement.pdf",
        "C:/Software_Development/documents/public/species/broiler/breeds/cobb/Cobb-MX-Male-Supplement.pdf",
        "C:/Software_Development/documents/public/species/broiler/breeds/cobb/Post-Mortem-Guide-_Breeders-2022-Digital-min.pdf",
        "C:/Software_Development/documents/public/species/broiler/breeds/ross_308_broiler/Aviagen_Ross_BroilerNutritionSupplement.pdf",
        "C:/Software_Development/documents/public/species/broiler/breeds/ross_308_broiler/Aviagen-ROSS-Broiler-Handbook-EN.pdf",
        "C:/Software_Development/documents/public/species/broiler/breeds/ross_308_broiler/Ross308FF-MgtSuppl2016EN.pdf",
        "C:/Software_Development/documents/public/species/broiler/breeds/ross_308_broiler/RossxRoss308-BroilerPerformanceObjectives2022-EN (1).pdf",
        "C:/Software_Development/documents/public/species/broiler/breeds/ross_308_parentstock/Aviagen_Ross_PS_Handbook_2023_Interactive_EN.pdf",
        "C:/Software_Development/documents/public/species/broiler/health/Gut-Health-on-the-Farm-Guide-EN.pdf",
        "C:/Software_Development/documents/public/species/broiler/housing/optimum-broiler-development.pdf",
        "C:/Software_Development/documents/public/species/broiler/value_chain/6e3727d0-bbd7-11e6-bd5d-55bb08833e29.pdf",
        "C:/Software_Development/documents/public/species/broiler/value_chain/Hatchery-Guide-Layout-R4-min.pdf",
        "C:/Software_Development/documents/public/species/layer/breeds/hy_line_brown/Hyline Brown ALT STD ENG.pdf",
        "C:/Software_Development/documents/public/species/layer/breeds/hy_line_brown/Hyline Brown Parent Stock ENG.pdf",
        "C:/Software_Development/documents/public/species/layer/breeds/hy_line_brown/Hyline Brown STD ENG.pdf",
        "C:/Software_Development/documents/public/species/layer/breeds/hy_line_w_36/Hyline W36- Conventional - Performance Sell Sheet ENG.pdf",
        "C:/Software_Development/documents/public/species/layer/breeds/hy_line_w_36/Hyline W36 Parent Stock ENG.pdf",
        "C:/Software_Development/documents/public/species/layer/breeds/hy_line_w_36/Hyline W36 STD ENG.pdf",
        "C:/Software_Development/documents/public/species/layer/breeds/hy_line_w_80/80 PS ENG.pdf",
        "C:/Software_Development/documents/public/species/layer/breeds/hy_line_w_80/80 STD ENG.pdf",
        "C:/Software_Development/documents/public/species/layer/breeds/lohmann_brown/LOHMANN-Brown-Classic-Cage.pdf",
        "C:/Software_Development/documents/public/species/layer/breeds/lohmann_lsl_classic/LOHMANN-LSL-Lite-Cage-1.pdf",
    ]

    # Initialize mapper
    mapper = PDFMigrationMapper(OLD_BASE, NEW_BASE)

    # Generate plan
    mapper.generate_migration_plan(pdf_files)

    # Export results
    mapper.export_migration_plan("C:/Software_Development/intelia-cognito/docs/implementation/migration_plan.json")
    mapper.generate_report("C:/Software_Development/intelia-cognito/docs/implementation/MIGRATION_REPORT.txt")

    print()
    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Review the generated reports:")
    print("   - docs/implementation/MIGRATION_REPORT.txt (human-readable)")
    print("   - docs/implementation/migration_plan.json (machine-readable)")
    print()
    print("2. To execute migration (DRY RUN):")
    print("   mapper.execute_migration(dry_run=True)")
    print()
    print("3. To execute migration (REAL):")
    print("   mapper.execute_migration(dry_run=False)")
    print("=" * 80)

    return mapper


if __name__ == "__main__":
    mapper = main()
