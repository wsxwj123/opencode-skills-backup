# Medical Research Assistant Skill

A comprehensive skill for medical and biomedical research workflows, integrating curated GitHub tools and best practices.

## What This Skill Does

This skill transforms Claude into an intelligent medical research assistant that can:

- **Guide literature reviews** with tool recommendations (Biomni, PubMedAI, bibliometrix)
- **Assist academic writing** using ScholarCopilot, PaperDebugger, and writing assistants
- **Create scientific visualizations** with Hiplot, FigureYaLLM, and 3D Slicer
- **Manage citations** with automated verification scripts
- **Plan research** with AI-powered research agents

## Installation

### For Claude Desktop/Code

1. Download `medical-research-assistant.zip`
2. Extract to your skills directory:
   - **macOS/Linux**: `~/.config/opencode/skills/`
   - **Windows**: `%APPDATA%\opencode\skills\`
3. Restart Claude

### For Other Platforms

Follow your platform's skill installation instructions.

## How to Use

Simply ask Claude research-related questions, and the skill will automatically activate:

### Example Queries

**Literature Review**:
- "Help me find recent papers on cancer immunotherapy"
- "I need to do a systematic literature review"
- "Analyze citation networks in my research area"

**Academic Writing**:
- "Help me write the introduction for my research paper"
- "Review my methods section for clarity"
- "Check my paper for structural issues"

**Data Visualization**:
- "Create a survival curve for my clinical trial data"
- "What's the best way to visualize gene expression data?"
- "Help me create publication-quality figures"

**Citation Management**:
- "Verify all citations in my paper"
- "Check if any citations are missing DOIs"

**Research Planning**:
- "Help me design a clinical trial"
- "What research gaps exist in Alzheimer's disease?"

## Features

### Intelligent Tool Recommendations

The skill recommends tools based on:
- Your research task (literature review, writing, visualization, etc.)
- Your expertise level (beginner, intermediate, advanced)
- Your research domain (clinical, basic science, epidemiology, etc.)

### Integrated Workflows

Get complete workflows for:
- Writing a research paper from scratch
- Conducting systematic reviews
- Creating data-heavy publications

### Curated Tool Catalog

Access 20+ vetted GitHub tools including:
- **Biomni**: Stanford's biomedical research assistant
- **ScholarCopilot**: TIGER-AI-Lab's writing assistant
- **bibliometrix**: R package for citation analysis (593 stars)
- **Hiplot**: Web-based visualization platform
- **PaperDebugger**: AI-powered paper review tool

### Citation Verification

Included Python script that:
- Extracts DOIs from your papers
- Verifies citations against CrossRef
- Reports invalid or missing citations

## Skill Structure

```
medical-research-assistant/
├── SKILL.md                          # Main skill instructions
├── scripts/
│   └── verify_citations.py           # Citation verification tool
├── references/
│   └── tools_catalog.md              # Detailed tool information
└── README.md                         # This file
```

## Requirements

### For Citation Verification Script

```bash
pip install requests
```

### For Recommended Tools

Most tools are optional and can be installed as needed:
- **Python tools**: Biomni, ScholarCopilot, PaperDebugger
- **R tools**: bibliometrix
- **Web tools**: Hiplot (no installation required)
- **Desktop tools**: 3D Slicer

The skill will guide you through installation when you choose to use specific tools.

## Examples

### Complete Paper Writing Workflow

```
User: "I need to write a research paper on diabetes treatment outcomes"

Claude (using skill):
1. Recommends Biomni for literature search
2. Suggests bibliometrix for citation analysis
3. Guides through ScholarCopilot for writing
4. Recommends Hiplot for creating figures
5. Offers PaperDebugger for final review
6. Provides citation verification script
```

### Quick Visualization

```
User: "Create a Kaplan-Meier survival curve"

Claude (using skill):
1. Assesses data format
2. Recommends Hiplot for web-based plotting
3. Provides step-by-step guidance
4. Suggests export options for publication
```

## Tips for Best Results

1. **Be specific** about your research task
2. **Mention your expertise level** (beginner/intermediate/advanced)
3. **Indicate any tool preferences** or constraints
4. **Ask for alternatives** if a tool doesn't work for you
5. **Request integrated workflows** for complex projects

## Troubleshooting

**Skill not activating?**
- Ensure the skill is in the correct directory
- Restart Claude
- Try explicit trigger: "Use medical research assistant skill"

**Tool recommendations not working?**
- Provide more context about your task
- Specify your expertise level
- Mention any constraints (OS, software access, etc.)

**Citation script errors?**
- Ensure Python 3 is installed
- Install requests: `pip install requests`
- Check file path is correct

## Updates

This skill includes tools that are actively developed. Check GitHub repositories for updates:
- **Monthly**: ScholarCopilot, PaperDebugger
- **Quarterly**: Biomni, bibliometrix
- **Annually**: 3D Slicer, Hiplot

## Contributing

Found a useful medical research tool? Suggestions for improvement?
- Open an issue on the skill repository
- Submit a pull request with tool additions
- Share your research workflows

## License

This skill is provided as-is for research and educational purposes. Individual tools have their own licenses (see tools_catalog.md).

## Citation

If this skill helps your research, consider citing the tools you use. Many have associated publications listed in the tools catalog.

## Support

For questions or issues:
1. Check the tools_catalog.md reference
2. Search tool GitHub repositories
3. Ask Claude for troubleshooting help
4. Open an issue on the skill repository

---

**Version**: 1.0.0
**Last Updated**: January 2026
**Curated Tools**: 20+
**Supported Workflows**: Literature review, writing, visualization, citation management, research planning
