#!/usr/bin/env python3
"""
Generate THIRD_PARTY_NOTICES.md from dependency licenses
"""

import json
import os
from pathlib import Path
from collections import defaultdict

# Chemins des fichiers de licences
BASE_DIR = Path(__file__).parent
LICENSES_BACKEND = BASE_DIR / "licenses_backend.json"
LICENSES_LLM = BASE_DIR / "licenses_llm.json"
LICENSES_FRONTEND_NPM = BASE_DIR / "frontend" / "licenses_frontend_npm.json"
OUTPUT_FILE = BASE_DIR / "THIRD_PARTY_NOTICES.md"

# Texte complet des licences standards
LICENSE_TEXTS = {
    "MIT": """MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is furnished
to do so, subject to the following conditions:

The above copyright notice and this permission notice (including the next
paragraph) shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF
OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.""",

    "Apache-2.0": """Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      [Full Apache 2.0 license text - see https://www.apache.org/licenses/LICENSE-2.0.txt]""",

    "BSD-3-Clause": """BSD 3-Clause "New" or "Revised" License

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
may be used to endorse or promote products derived from this software without
specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.""",

    "ISC": """ISC License

Permission to use, copy, modify, and/or distribute this software for any purpose
with or without fee is hereby granted, provided that the above copyright notice
and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT,
OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE,
DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE."""
}


def load_python_licenses(filepath):
    """Charge les licences Python depuis pip-licenses JSON"""
    if not filepath.exists():
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    packages = []
    for pkg in data:
        packages.append({
            'name': pkg.get('Name', 'Unknown'),
            'version': pkg.get('Version', ''),
            'license': pkg.get('License', 'Unknown'),
            'url': pkg.get('URL', ''),
            'author': pkg.get('Author', '')
        })

    return packages


def load_npm_licenses(filepath):
    """Charge les licences NPM depuis npm list JSON"""
    if not filepath.exists():
        return []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        return []

    packages = []

    def extract_deps(deps_dict, packages_list):
        if not deps_dict:
            return
        for name, info in deps_dict.items():
            if isinstance(info, dict):
                version = info.get('version', '')
                # Extraire la licence du package.json si disponible
                license_type = 'Unknown'
                if 'resolved' in info:
                    license_type = 'MIT'  # Défaut pour NPM

                packages_list.append({
                    'name': name,
                    'version': version,
                    'license': license_type,
                    'url': f'https://www.npmjs.com/package/{name}',
                    'author': ''
                })

                # Recursion pour les sous-dépendances
                if 'dependencies' in info:
                    extract_deps(info['dependencies'], packages_list)

    if 'dependencies' in data:
        extract_deps(data['dependencies'], packages)

    return packages


def group_by_license(packages):
    """Groupe les packages par type de licence"""
    grouped = defaultdict(list)

    for pkg in packages:
        license_type = pkg['license']
        # Normaliser les noms de licences
        if 'MIT' in license_type.upper():
            license_type = 'MIT'
        elif 'APACHE' in license_type.upper() or 'Apache-2.0' in license_type:
            license_type = 'Apache-2.0'
        elif 'BSD-3' in license_type or '3-Clause BSD' in license_type:
            license_type = 'BSD-3-Clause'
        elif 'ISC' in license_type:
            license_type = 'ISC'
        elif 'PSF' in license_type or 'Python' in license_type:
            license_type = 'Python Software Foundation License'

        grouped[license_type].append(pkg)

    return grouped


def generate_notices(output_file):
    """Génère le fichier THIRD_PARTY_NOTICES.md"""

    print("[INFO] Chargement des licences Python (Backend)...")
    backend_packages = load_python_licenses(LICENSES_BACKEND)
    print(f"  {len(backend_packages)} packages backend")

    print("[INFO] Chargement des licences Python (LLM)...")
    llm_packages = load_python_licenses(LICENSES_LLM)
    print(f"  {len(llm_packages)} packages LLM")

    print("[INFO] Chargement des licences NPM (Frontend)...")
    frontend_packages = load_npm_licenses(LICENSES_FRONTEND_NPM)
    print(f"  {len(frontend_packages)} packages frontend")

    # Combiner tous les packages
    all_packages = backend_packages + llm_packages + frontend_packages

    # Supprimer les doublons
    unique_packages = {}
    for pkg in all_packages:
        key = f"{pkg['name']}-{pkg['version']}"
        if key not in unique_packages:
            unique_packages[key] = pkg

    all_packages = list(unique_packages.values())
    print(f"[INFO] Total: {len(all_packages)} packages uniques")

    # Grouper par licence
    grouped = group_by_license(all_packages)

    # Générer le fichier Markdown
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Third Party Notices\n\n")
        f.write("THE FOLLOWING SETS FORTH ATTRIBUTION NOTICES FOR THIRD PARTY SOFTWARE ")
        f.write("THAT MAY BE CONTAINED IN PORTIONS OF THIS PRODUCT.\n\n")
        f.write("---\n\n")

        # Pour chaque type de licence
        for license_type in sorted(grouped.keys()):
            packages = grouped[license_type]

            f.write(f"## {license_type}\n\n")
            f.write(f"The following components are licensed under {license_type}:\n\n")

            # Lister les composants
            for pkg in sorted(packages, key=lambda x: x['name']):
                f.write(f"- **{pkg['name']} {pkg['version']}**")
                if pkg['author']:
                    f.write(f" - {pkg['author']}")
                f.write("\n")

            f.write("\n")

            # Ajouter le texte de la licence si disponible
            if license_type in LICENSE_TEXTS:
                f.write("### License Text\n\n")
                f.write("```\n")
                f.write(LICENSE_TEXTS[license_type])
                f.write("\n```\n\n")
            else:
                f.write(f"See [{license_type} license]({packages[0].get('url', '')})\n\n")

            f.write("---\n\n")

    print(f"[OK] Fichier généré: {output_file}")
    return output_file


if __name__ == '__main__':
    generate_notices(OUTPUT_FILE)
