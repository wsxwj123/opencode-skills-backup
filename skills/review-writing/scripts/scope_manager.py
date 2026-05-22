import os
import re
import json
import argparse
import sys
from pathlib import Path

class ScopeManager:
    def __init__(self, project_root='.'):
        self.project_root = Path(project_root)
        self.storyline_path = self.project_root / 'storyline.md'
        self.progress_path = self.project_root / 'progress.json'
        self.drafts_dir = self.project_root / 'drafts'
        self.sections = []
        self.content = ""
        
        if self.storyline_path.exists():
            self.load_storyline()

    def load_storyline(self):
        with open(self.storyline_path, 'r', encoding='utf-8') as f:
            self.content = f.read()
        
        # Regex to find Level 2 headers: ## X. Title
        # Captures the full line content after ##
        self.sections = []
        pattern = re.compile(r'^##\s+(.+)$', re.MULTILINE)
        for match in pattern.finditer(self.content):
            self.sections.append({
                'title': match.group(1).strip(),
                'start': match.start(),
                'end': match.end()
            })

    def _save_storyline(self):
        with open(self.storyline_path, 'w', encoding='utf-8') as f:
            f.write(self.content)
        self.load_storyline()

    def add_section(self, title, after=None):
        new_section_block = f"\n\n## {title}\n(Content to be added)\n"
        
        if after:
            # Find the 'after' section
            target_idx = -1
            for i, section in enumerate(self.sections):
                if section['title'] == after:
                    target_idx = i
                    break
            
            if target_idx == -1:
                print(f"Warning: Section '{after}' not found. Appending to end.")
                self.content += new_section_block
            else:
                # We need to insert after the CONTENT of this section, 
                # effectively before the NEXT section starts.
                if target_idx + 1 < len(self.sections):
                    next_start = self.sections[target_idx + 1]['start']
                    self.content = self.content[:next_start] + f"## {title}\n(Content to be added)\n\n" + self.content[next_start:]
                else:
                    self.content += new_section_block
        else:
            self.content += new_section_block
            
        self._save_storyline()
        print(f"Added section: {title}")

    def remove_section(self, title, force=False):
        section_to_remove = next((s for s in self.sections if s['title'] == title), None)
        if not section_to_remove:
            print(f"Error: Section '{title}' not found.")
            return

        if not force:
            # Check safeguards
            # 1. Progress.json
            if self.progress_path.exists():
                with open(self.progress_path, 'r') as f:
                    progress = json.load(f)
                
                # Check active or completed
                if title == progress.get('active_section'):
                    raise ValueError(f"Cannot remove active section '{title}' without --force")
                if title in progress.get('completed_sections', []):
                    raise ValueError(f"Cannot remove completed section '{title}' without --force")

            # 2. Drafts check
            # Try to infer filename pattern: ID_Topic
            # E.g. "2. Methods" -> "02_Methods.md" or "2_Methods.md"
            # Simple fuzzy check: if any file in drafts contains the main words
            if self.drafts_dir.exists():
                # Extract simplified alphanumeric parts for matching
                clean_title = re.sub(r'[^\w\s]', '', title) # 2 Methods
                parts = clean_title.split()
                # If we have "2" and "Methods", look for them
                for file in self.drafts_dir.glob('*.md'):
                    if all(part in file.name for part in parts if len(part) > 1):
                         raise ValueError(f"Draft file {file.name} likely associated with section. Use --force.")

        # Perform removal
        # Remove from '## Title' up to next '##'
        start_idx = section_to_remove['start']
        
        # Find index of this section in list to get next section
        curr_idx = self.sections.index(section_to_remove)
        if curr_idx + 1 < len(self.sections):
            end_idx = self.sections[curr_idx + 1]['start']
        else:
            end_idx = len(self.content)

        self.content = self.content[:start_idx] + self.content[end_idx:]
        self._save_storyline()
        print(f"Removed section: {title}")

    def rename_section(self, old_title, new_title):
        section = next((s for s in self.sections if s['title'] == old_title), None)
        if not section:
            print(f"Error: Section '{old_title}' not found.")
            return

        # 1. Update Storyline
        # Simple replace might be dangerous if title is common word, but these are full headers
        # We know the start position, let's use that.
        # But 'start' points to beginning of '## Title', wait.
        # My regex captured the group(1) (title only) but match object has start/end of the WHOLE MATCH including ##
        # Let's look at load_storyline again. 
        # match = re.compile(r'^##\s+(.+)$', ...). match.start() is start of line '## ...'
        
        # Actually simplest is just regex replace on that specific header line
        # Or string replacement if unique.
        # Safer: Reconstruct content using the known indices.
        
        # Let's just do a replace on the specific substring at that location to be safe
        # Re-read to ensure indices are fresh (load_storyline is called in __init__ and _save)
        
        # The content at section['start'] should start with "## "
        # We want to replace "## old_title" with "## new_title"
        
        # Locate exact line
        header_line = f"## {old_title}"
        new_header_line = f"## {new_title}"
        
        # Because we might have multiple similar titles, we should use the index
        # But content modification shifts indices. We haven't modified yet.
        # Verify
        actual_segment = self.content[section['start']:section['end']]
        if old_title not in actual_segment:
             print("Error: Index mismatch during rename.")
             return

        self.content = self.content[:section['start']] + new_header_line + self.content[section['end']:]
        self._save_storyline() # Reloads sections

        # 2. Update Progress.json
        if self.progress_path.exists():
            with open(self.progress_path, 'r') as f:
                progress = json.load(f)
            
            changed = False
            if progress.get('active_section') == old_title:
                progress['active_section'] = new_title
                changed = True
            
            if old_title in progress.get('completed_sections', []):
                idx = progress['completed_sections'].index(old_title)
                progress['completed_sections'][idx] = new_title
                changed = True
                
            if changed:
                with open(self.progress_path, 'w') as f:
                    json.dump(progress, f, indent=2)
                    
        print(f"Renamed '{old_title}' to '{new_title}'")

def main():
    parser = argparse.ArgumentParser(description="Manage review scope (sections)")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Add
    add_parser = subparsers.add_parser('add', help='Add a new section')
    add_parser.add_argument('title', help='Title of the new section')
    add_parser.add_argument('--after', help='Insert after this section title')

    # Remove
    rm_parser = subparsers.add_parser('remove', help='Remove a section')
    rm_parser.add_argument('title', help='Title of the section to remove')
    rm_parser.add_argument('--force', action='store_true', help='Force removal even if drafts exist')

    # Rename
    rn_parser = subparsers.add_parser('rename', help='Rename a section')
    rn_parser.add_argument('old', help='Current title')
    rn_parser.add_argument('new', help='New title')

    # List
    list_parser = subparsers.add_parser('list', help='List current sections')

    args = parser.parse_args()
    
    manager = ScopeManager() # Defaults to current dir
    
    if args.command == 'add':
        manager.add_section(args.title, args.after)
    elif args.command == 'remove':
        try:
            manager.remove_section(args.title, args.force)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    elif args.command == 'rename':
        manager.rename_section(args.old, args.new)
    elif args.command == 'list':
        for s in manager.sections:
            print(s['title'])
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
