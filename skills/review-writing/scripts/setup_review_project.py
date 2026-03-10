#!/usr/bin/env python3
import os
import json
import argparse
from datetime import datetime

def setup_project(base_path, topic):
    """Initialize the directory structure for a literature review project."""
    
    # Create main project directory
    timestamp = datetime.now().strftime("%Y%m%d")
    project_name = f"Review_{timestamp}_{topic.replace(' ', '_')}"
    project_path = os.path.join(base_path, project_name)
    
    os.makedirs(project_path, exist_ok=True)
    
    # Create subdirectories
    dirs = [
        "drafts",          # Individual section drafts
        "data",            # Raw data, synthesis matrix, SI
        "logs",            # Conversation history/context snapshots
        "figures"          # Figure ideas and captions
    ]
    
    for d in dirs:
        os.makedirs(os.path.join(project_path, d), exist_ok=True)
        
    # 1. Project Info (Basic Information)
    info_content = f"""# Project Information
**Topic:** {topic}
**Date:** {datetime.now().strftime("%Y-%m-%d")}
**Target Journal:** (e.g., Nature Reviews, Cell, Lancet Digital Health)
**Research Question (RQ):** [To be defined]
**PICO Criteria:**
- **P**opulation: 
- **I**ntervention: 
- **C**omparison: 
- **O**utcome: 
"""
    with open(os.path.join(project_path, "project_info.md"), "w") as f:
        f.write(info_content)

    # 2. Data Files (JSON)
    # Literature Index
    with open(os.path.join(project_path, "data", "literature_index.json"), "w") as f:
        json.dump([], f)
    
    # Synthesis Matrix (New)
    with open(os.path.join(project_path, "data", "synthesis_matrix.json"), "w") as f:
        json.dump([], f)

    # Copy Matrix Schema
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "..", "templates", "matrix_schema.json")
    try:
        if os.path.exists(template_path):
            with open(template_path, 'r') as src:
                schema_content = src.read()
            with open(os.path.join(project_path, "data", "matrix_schema.json"), "w") as dst:
                dst.write(schema_content)
        else:
            # Fallback if template missing (shouldn't happen in proper install)
            default_schema = {
                "_instruction": "Extract these fields. If N/A, write 'N/A'.",
                "fields": ["Delivery System", "Preparation Method", "Drug Release Mechanism", 
                          "Targeting Strategy", "Disease Model", "Key Target/Pathway", 
                          "Administration Route", "Key Finding", "Contribution", "Limitation"]
            }
            with open(os.path.join(project_path, "data", "matrix_schema.json"), "w") as dst:
                json.dump(default_schema, dst, indent=2)
    except Exception as e:
        print(f"Warning: Could not copy matrix_schema.json: {e}")
        
    # SI Database (New)
    with open(os.path.join(project_path, "data", "si_database.json"), "w") as f:
        json.dump([], f)
        
    # 3. Figure Index
    fig_content = """# Figure & Table Index

Use this file to plan figures and tables.

## Table 1: [Title]
- **Content:**
- **Caption:**

## Figure 1: [Title]
- **Concept:**
- **Caption:**
"""
    with open(os.path.join(project_path, "figures", "figure_index.md"), "w") as f:
        f.write(fig_content)
        
    # 4. Storyline (Outline)
    outline_content = """# Review Outline & Storyline

## 1. Introduction
- [Status: Pending]
- Key Points:

## 2. [Section Title]
- [Status: Pending]
- Key Points:

## 3. [Section Title]
- [Status: Pending]
- Key Points:

## 4. Conclusion & Perspectives
- [Status: Pending]
- Key Points:
"""
    with open(os.path.join(project_path, "storyline.md"), "w") as f:
        f.write(outline_content)
        
    # 5. Progress Tracker
    progress = {
        "topic": topic,
        "current_stage": "Deconstruction",
        "completed_sections": [],
        "pending_sections": ["Introduction", "Body", "Conclusion"],
        "total_citations": 0
    }
    with open(os.path.join(project_path, "progress.json"), "w") as f:
        json.dump(progress, f, indent=2)
        
    # 6. Context Memory (Log)
    with open(os.path.join(project_path, "logs", "context_memory.md"), "w") as f:
        f.write("# Context Memory\n\nInitial state created.")

    print(f"✅ Project initialized at: {project_path}")
    print(f"Structure created: drafts/, data/, logs/, figures/")
    print(f"Files created: project_info.md, literature_index.json, synthesis_matrix.json, storyline.md, progress.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup a literature review project structure")
    parser.add_argument("topic", help="Short topic name for the review")
    parser.add_argument("--path", default=".", help="Base path for the project")
    
    args = parser.parse_args()
    setup_project(args.path, args.topic)
