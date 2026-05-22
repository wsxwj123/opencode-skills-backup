#!/usr/bin/env python3
"""
Citation Verification Script
Extracts DOIs from text and verifies citations using CrossRef API
"""

import re
import requests
from typing import List, Dict
import sys

class CitationVerifier:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CitationVerifier/1.0 (Medical Research Assistant)'
        })

    def extract_dois(self, text: str) -> List[str]:
        """Extract all DOIs from text."""
        doi_pattern = r'10\.\d{4,}/[^\s\]\)"<>]+'
        dois = re.findall(doi_pattern, text)
        return list(set(dois))  # Remove duplicates

    def verify_doi(self, doi: str) -> Dict:
        """Verify a single DOI using CrossRef API."""
        url = f"https://api.crossref.org/works/{doi}"
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    'doi': doi,
                    'valid': True,
                    'title': data['message'].get('title', [''])[0],
                    'authors': self._format_authors(data['message'].get('author', [])),
                    'year': self._extract_year(data['message'])
                }
            else:
                return {'doi': doi, 'valid': False, 'error': 'DOI not found'}
        except Exception as e:
            return {'doi': doi, 'valid': False, 'error': str(e)}

    def _format_authors(self, authors: List[Dict]) -> str:
        """Format author list."""
        if not authors:
            return "Unknown"
        if len(authors) == 1:
            return f"{authors[0].get('family', '')}, {authors[0].get('given', '')}"
        elif len(authors) <= 3:
            return "; ".join([f"{a.get('family', '')}, {a.get('given', '')}" for a in authors])
        else:
            return f"{authors[0].get('family', '')}, {authors[0].get('given', '')} et al."

    def _extract_year(self, message: Dict) -> str:
        """Extract publication year."""
        if 'published-print' in message:
            return str(message['published-print']['date-parts'][0][0])
        elif 'published-online' in message:
            return str(message['published-online']['date-parts'][0][0])
        return "Unknown"

    def verify_file(self, filepath: str) -> List[Dict]:
        """Verify all citations in a file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        
        dois = self.extract_dois(text)
        print(f"Found {len(dois)} unique DOIs")
        
        results = []
        for i, doi in enumerate(dois, 1):
            print(f"Verifying {i}/{len(dois)}: {doi}")
            result = self.verify_doi(doi)
            results.append(result)
        
        return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_citations.py <file_path>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    verifier = CitationVerifier()
    results = verifier.verify_file(filepath)
    
    print("\n" + "="*80)
    print("CITATION VERIFICATION RESULTS")
    print("="*80)
    
    valid_count = sum(1 for r in results if r.get('valid'))
    print(f"\nTotal DOIs: {len(results)}")
    print(f"Valid: {valid_count}")
    print(f"Invalid: {len(results) - valid_count}")
    
    print("\nDETAILS:")
    for result in results:
        print(f"\nDOI: {result['doi']}")
        if result.get('valid'):
            print(f"  ✓ Valid")
            print(f"  Title: {result.get('title', 'N/A')}")
            print(f"  Authors: {result.get('authors', 'N/A')}")
            print(f"  Year: {result.get('year', 'N/A')}")
        else:
            print(f"  ✗ Invalid: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
