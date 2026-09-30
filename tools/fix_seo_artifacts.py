#!/usr/bin/env python3
"""
fix_seo_artifacts.py
---------------------
Post-build utility for SoftCloud MyST documentation sites.
Ensures:
1. robots.txt declares canonical domain and Sitemap URL.
2. sitemap.xml contains valid canonical HTTPS URLs (replacing default localhost:3000).
3. Strips ignored tags (<changefreq>, <priority>) and verifies XML validity.
"""

import sys
import os
import re
import xml.etree.ElementTree as ET

def process_site(domain: str, html_dir: str):
    domain = domain.rstrip('/')
    if not os.path.isdir(html_dir):
        print(f"Error: {html_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    # 1. robots.txt
    robots_path = os.path.join(html_dir, "robots.txt")
    robots_content = f"""User-agent: *
Allow: /
Sitemap: {domain}/sitemap.xml
"""
    with open(robots_path, "w", encoding="utf-8") as f:
        f.write(robots_content)
    print(f"[OK] Written {robots_path} with Sitemap: {domain}/sitemap.xml")

    # 2. sitemap.xml
    sitemap_path = os.path.join(html_dir, "sitemap.xml")
    if os.path.isfile(sitemap_path):
        with open(sitemap_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace localhost:3000 or http variant with production canonical domain
        content = re.sub(r'https?://localhost:3000/?', f"{domain}/", content)
        content = re.sub(rf'{domain}//', f"{domain}/", content)

        # Parse XML to validate and clean up unnecessary tags
        try:
            # Handle potential xml-stylesheet header
            stylesheet_match = re.search(r'<\?xml-stylesheet.*?\?>', content)
            stylesheet_tag = stylesheet_match.group(0) if stylesheet_match else ""
            if stylesheet_tag:
                stylesheet_tag = re.sub(r'https?://localhost:3000/?', f"{domain}/", stylesheet_tag)

            # Strip xml processing instructions for parsing
            xml_body = re.sub(r'<\?xml.*?\?>', '', content).strip()
            ET.register_namespace('', "http://www.sitemaps.org/schemas/sitemap/0.9")
            root = ET.fromstring(xml_body)

            # Remove changefreq and priority if present (Google ignores them)
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            for url in root.findall('sm:url', ns):
                cf = url.find('sm:changefreq', ns)
                if cf is not None:
                    url.remove(cf)
                pr = url.find('sm:priority', ns)
                if pr is not None:
                    url.remove(pr)

            new_xml = ET.tostring(root, encoding='utf-8', xml_declaration=True).decode('utf-8')
            if stylesheet_tag and stylesheet_tag not in new_xml:
                # Re-insert stylesheet after xml declaration
                parts = new_xml.split('\n', 1)
                new_xml = parts[0] + '\n' + stylesheet_tag + '\n' + (parts[1] if len(parts) > 1 else '')

            with open(sitemap_path, "w", encoding="utf-8") as f:
                f.write(new_xml)
            print(f"[OK] Validated and transformed {sitemap_path}")
        except Exception as e:
            print(f"[WARN] XML parsing error: {e}. Writing raw regex-replaced content.", file=sys.stderr)
            with open(sitemap_path, "w", encoding="utf-8") as f:
                f.write(content)
    else:
        # Fallback generator if MyST didn't produce sitemap.xml
        print(f"[INFO] sitemap.xml not found in {html_dir}, generating from HTML routes...")
        routes = []
        for root_dir, _, files in os.walk(html_dir):
            for file in files:
                if file.endswith(".html") and not file.startswith("404") and not file.startswith("_"):
                    rel = os.path.relpath(os.path.join(root_dir, file), html_dir)
                    if rel == "index.html":
                        route = f"{domain}/"
                    elif rel.endswith("/index.html"):
                        route = f"{domain}/{rel[:-10]}/"
                    else:
                        route = f"{domain}/{rel[:-5]}"
                    routes.append(route)

        routes.sort()
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        ]
        for r in routes:
            xml_lines.append(f'  <url>\n    <loc>{r}</loc>\n  </url>')
        xml_lines.append('</urlset>')
        with open(sitemap_path, "w", encoding="utf-8") as f:
            f.write('\n'.join(xml_lines) + '\n')
        print(f"[OK] Generated fallback {sitemap_path} with {len(routes)} routes")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: fix_seo_artifacts.py <canonical_domain_url> <html_output_directory>")
        print("Example: fix_seo_artifacts.py https://linux.softcloud.dev _build/html")
        sys.exit(1)
    process_site(sys.argv[1], sys.argv[2])
