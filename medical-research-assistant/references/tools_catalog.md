# Medical Research Tools Catalog

This catalog contains detailed information about curated GitHub tools for medical research.

## Literature Review & Management Tools

### Biomni (Stanford)
- **GitHub**: https://github.com/snap-stanford/Biomni
- **License**: Apache-2.0
- **Description**: Expert biomedical research assistant with comprehensive resource integration
- **Key Features**:
  - Integrates PubMed, protein databases, clinical trials
  - Intelligent resource selection based on queries
  - Full-text paper retrieval
  - Biomedical entity recognition
- **Best For**: Comprehensive biomedical literature searches, multi-database queries
- **Installation**: Python-based, requires API keys for some features
- **Usage Example**: Query biomedical databases with natural language

### PubMedAI
- **GitHub**: https://github.com/PubMedAI/aiforpubmed
- **Description**: AI-enhanced PubMed search and analysis
- **Key Features**:
  - Smart PubMed filtering
  - AI-powered relevance ranking
  - Abstract summarization
- **Best For**: Focused PubMed searches, quick literature screening
- **Installation**: Web-based or Python API

### bibliometrix (R Package)
- **GitHub**: https://github.com/massimoaria/bibliometrix
- **Stars**: 593
- **License**: Multiple licenses
- **Description**: Comprehensive science mapping and bibliometric analysis
- **Key Features**:
  - Citation network visualization
  - Research trend analysis
  - Co-authorship networks
  - Journal impact analysis
- **Best For**: Systematic reviews, research landscape analysis, citation analysis
- **Installation**: R package - `install.packages("bibliometrix")`
- **Website**: www.bibliometrix.org

### AI Tools for Literature Review
- **GitHub**: https://github.com/drshahizan/ai-tools
- **Description**: Curated collection of AI-powered literature review tools
- **Key Features**:
  - Machine learning for literature analysis
  - Automated synthesis
  - Gap identification
- **Best For**: Discovering new literature review tools

## Academic Writing Tools

### ScholarCopilot (TIGER-AI-Lab)
- **GitHub**: https://github.com/TIGER-AI-Lab/ScholarCopilot
- **License**: MIT
- **Description**: Intelligent academic writing assistant with AI-powered suggestions
- **Key Features**:
  - Next-3-sentence suggestions
  - Contextual citation recommendations
  - Real-time writing assistance
  - Academic tone optimization
- **Best For**: Drafting papers, maintaining academic style, citation integration
- **Paper**: Accepted to COLM 2025
- **Installation**: Python-based with Gradio interface

### PaperDebugger
- **GitHub**: https://github.com/PaperDebugger/paperdebugger
- **License**: AGPL-3.0
- **Description**: AI-powered paper review and improvement tool
- **Key Features**:
  - Overleaf integration
  - Multi-step reasoning (Research → Critique → Revision)
  - Reviewer-style critique
  - Structured revision passes
- **Best For**: Paper debugging, comprehensive review, iterative improvement
- **Installation**: Chrome extension + backend service
- **Chrome Store**: Available

### Academic Writing Assistant (Multiple Implementations)
- **GitHub**: 
  - https://github.com/Theigrams/Academic-Writing-Assistant
  - https://github.com/lobehub/lobe-chat-agents (agent version)
- **License**: MIT
- **Description**: Formal academic writing style and structure guidance
- **Key Features**:
  - Academic tone checking
  - Structure validation
  - Citation format verification
  - Terminology consistency
- **Best For**: Style polishing, format compliance, academic conventions

### K-Dense-AI Scientific Writer
- **GitHub**: https://github.com/K-Dense-AI/claude-scientific-writer
- **Description**: General-purpose scientific writing assistant
- **Key Features**:
  - Scientific writing templates
  - Citation verification scripts
  - Literature review workflows
- **Best For**: Scientific writing workflows, citation management

## Data Visualization Tools

### Hiplot
- **GitHub**: https://github.com/hiplot/docs
- **Website**: https://hiplot.org
- **Description**: Comprehensive web-based biomedical visualization platform
- **Key Features**:
  - 300+ chart types
  - Web interface (no installation)
  - Publication-quality outputs
  - Interactive visualizations
- **Best For**: General biomedical charts, quick visualizations, web-based work
- **Installation**: Web-based, no installation required

### FigureYaLLM
- **GitHub**: https://github.com/xuzhougeng/FigureYaLLM
- **Description**: Intelligent biomedical visualization module recommendation system
- **Key Features**:
  - 317+ visualization modules
  - LLM-powered recommendations
  - Direct links to module documentation
  - Google-like search interface
- **Best For**: Choosing appropriate visualization types, discovering new chart options
- **Installation**: Docker containerization available

### 3D Slicer / SlicerMorph
- **GitHub**: https://github.com/SlicerMorph/SlicerMorph
- **License**: BSD-2-Clause
- **Description**: Professional 3D biomedical visualization platform
- **Key Features**:
  - Medical image analysis
  - 3D reconstruction
  - Morphological analysis
  - Subject-specific visualization
- **Best For**: Medical imaging, 3D visualizations, morphometric analysis
- **Installation**: Desktop application (Windows/Mac/Linux)
- **Citation**: Kikinis et al., 2014

## Research Planning Tools

### Medical Research Agents
- **GitHub**: 
  - https://github.com/ed-donner/agents (medical paper planner)
  - https://github.com/MervinPraison/PraisonAI (medical researcher agent)
- **License**: MIT
- **Description**: AI agents for medical research planning and literature search
- **Key Features**:
  - Academic literature search planning
  - Medical terminology support
  - MeSH term integration
  - Research gap identification
- **Best For**: Research design, hypothesis formulation, literature planning

### Scientific Paper Agent (LangGraph)
- **GitHub**: https://github.com/NirDiamant/GenAI_Agents
- **License**: MIT
- **Description**: Multi-agent system for scientific paper workflows
- **Key Features**:
  - LangGraph-based orchestration
  - Multi-step research processes
  - Agent collaboration
- **Best For**: Complex research workflows, automated research tasks

## Citation Management Tools

### Citation Verification Scripts
- **Location**: Included in this skill (scripts/verify_citations.py)
- **Source**: https://github.com/K-Dense-AI/claude-scientific-skills
- **Description**: Automated citation verification and DOI extraction
- **Key Features**:
  - DOI extraction from text
  - Citation validation
  - CrossRef API integration
  - Batch processing
- **Best For**: Verifying citations before submission, finding missing DOIs

### Literature Review Tools
- **GitHub**: https://github.com/cyharyanto/llassist
- **License**: AGPL-3.0
- **Description**: Literature review assistant with AI capabilities
- **Key Features**:
  - Streamlined review process
  - AI-powered organization
  - Citation management
- **Best For**: Systematic reviews, literature organization

## Comprehensive Research Platforms

### AI for Science (Awesome List)
- **GitHub**: https://github.com/ai-boost/awesome-ai-for-science
- **Description**: Curated list of AI tools for scientific discovery
- **Coverage**: Physics, chemistry, biology, materials science, medicine
- **Best For**: Discovering new tools, staying updated on AI research tools

### Research Paper Writer Swarm
- **GitHub**: https://github.com/The-Swarm-Corporation/Research-Paper-Writer-Swarm
- **Description**: Automated research paper writing system
- **Best For**: Automated paper generation workflows

## Tool Selection Matrix

| Task | Beginner | Intermediate | Advanced |
|------|----------|--------------|----------|
| Literature Search | PubMedAI | Biomni | Biomni + bibliometrix |
| Writing | Academic Writing Assistant | ScholarCopilot | ScholarCopilot + PaperDebugger |
| Visualization | Hiplot | Hiplot + FigureYaLLM | 3D Slicer (imaging) |
| Citations | Manual + verification script | Citation verification script | K-Dense-AI tools |
| Planning | Medical Research Agents | Scientific Paper Agent | Custom agent workflows |

## Installation Priority

### Essential (Start Here)
1. **Hiplot** - Web-based, no installation
2. **Academic Writing Assistant** - Easy setup
3. **Citation verification script** - Included in skill

### Recommended (Next Steps)
1. **ScholarCopilot** - Python installation
2. **bibliometrix** - R package
3. **PubMedAI** - Python/Web

### Advanced (When Needed)
1. **Biomni** - Complex setup, API keys required
2. **3D Slicer** - Large desktop application
3. **PaperDebugger** - Chrome extension + backend

## Integration Workflows

### Workflow 1: Complete Paper Writing
```
Biomni (literature) → bibliometrix (analysis) → 
ScholarCopilot (writing) → Hiplot (figures) → 
PaperDebugger (review) → Citation verification (final check)
```

### Workflow 2: Systematic Review
```
PubMedAI + Biomni (search) → bibliometrix (network analysis) → 
Academic Writing Assistant (synthesis) → Hiplot (PRISMA diagram)
```

### Workflow 3: Data-Heavy Paper
```
Research planning (agents) → Data analysis (external tools) → 
Hiplot/3D Slicer (visualization) → ScholarCopilot (writing) → 
Citation verification
```

## Update Frequency

- **Check monthly**: ScholarCopilot, PaperDebugger (active development)
- **Check quarterly**: Biomni, bibliometrix (stable releases)
- **Check annually**: 3D Slicer, Hiplot (mature projects)

## Community Resources

- **GitHub Discussions**: Most projects have active discussions
- **Documentation**: Check project wikis and docs folders
- **Issues**: Search existing issues before asking questions
- **Papers**: Many tools have associated publications for citation
