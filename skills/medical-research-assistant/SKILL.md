---
name: medical-research-assistant
description: Comprehensive medical research assistant that helps with literature review, research planning, paper writing, data visualization, and citation management. Use this skill when conducting medical/biomedical research, writing academic papers, analyzing scientific literature, or creating research visualizations. Triggers on queries about research methodology, paper writing, literature search, scientific figures, or academic workflows.
---

# Medical Research Assistant

## Overview

This skill provides comprehensive support for medical and biomedical research workflows, integrating curated GitHub tools and best practices for literature review, research planning, academic writing, data visualization, and citation management. It acts as an intelligent assistant that recommends appropriate tools and guides users through research tasks based on their specific needs.

## Quick Start

When a user requests research assistance, follow this decision tree:

1. **Identify the research phase**: Literature review, research planning, data analysis, writing, or visualization
2. **Assess user expertise**: Beginner, intermediate, or advanced researcher
3. **Recommend appropriate tools** from the curated toolkit (see references/tools_catalog.md)
4. **Provide step-by-step guidance** for the selected workflow
5. **Offer tool integration suggestions** for comprehensive workflows

## Core Capabilities

### 1. Literature Review & Management

**When to use**: User needs to search, organize, or analyze scientific literature

**Workflow**:
1. Clarify research topic and scope
2. Recommend appropriate search tools based on domain:
   - **Biomni**: For comprehensive biomedical literature with PubMed integration
   - **PubMedAI**: For focused PubMed searches with AI filtering
   - **bibliometrix**: For citation network analysis and research trends
3. Guide literature organization and synthesis
4. Suggest citation management approach

**Example queries**:
- "Help me find recent papers on cancer immunotherapy"
- "I need to do a systematic literature review on diabetes treatments"
- "Analyze citation networks in my research area"

**Tool recommendations**:
```
Primary: Biomni (biomedical focus) or PubMedAI (PubMed specific)
Secondary: bibliometrix (for citation analysis)
Integration: Export results to citation manager
```

### 2. Research Planning & Hypothesis Development

**When to use**: User needs help designing studies, formulating hypotheses, or planning experiments

**Workflow**:
1. Understand research question and objectives
2. Review existing literature for gaps (use Literature Review tools)
3. Help formulate testable hypotheses
4. Suggest appropriate methodologies
5. Identify potential data sources and analysis approaches

**Example queries**:
- "Help me design a clinical trial for a new drug"
- "What research gaps exist in Alzheimer's disease?"
- "How should I structure my research proposal?"

**Tool recommendations**:
```
Primary: Medical Research Agents (for planning and gap analysis)
Secondary: Biomni (for literature context)
Integration: Create research timeline and milestones
```

### 3. Academic Writing & Paper Composition

**When to use**: User needs to write, edit, or improve academic papers

**Workflow**:
1. Identify writing stage: outline, draft, revision, or final polish
2. Recommend appropriate writing tools:
   - **ScholarCopilot**: For AI-assisted writing with citation suggestions
   - **PaperDebugger**: For comprehensive paper review and improvement
   - **Academic Writing Assistant**: For style and format guidance
3. Provide section-specific guidance (Introduction, Methods, Results, Discussion)
4. Ensure proper citation format and academic tone

**Example queries**:
- "Help me write the introduction for my research paper"
- "Review my methods section for clarity"
- "Improve the academic tone of my discussion"
- "Check my paper for structural issues"

**Tool recommendations**:
```
Primary: ScholarCopilot (for writing assistance)
Secondary: PaperDebugger (for review and debugging)
Tertiary: Academic Writing Assistant (for style polish)
Integration: Overleaf or Word for final formatting
```

### 4. Data Visualization & Figure Creation

**When to use**: User needs to create scientific figures, charts, or visualizations

**Workflow**:
1. Understand data type and visualization goal
2. Recommend appropriate visualization tools:
   - **Hiplot**: For general biomedical visualizations (300+ chart types)
   - **FigureYaLLM**: For intelligent visualization recommendations
   - **3D Slicer**: For medical imaging and 3D visualizations
3. Guide figure design following scientific standards
4. Ensure publication-quality output

**Example queries**:
- "Create a survival curve for my clinical trial data"
- "What's the best way to visualize gene expression data?"
- "Help me create publication-quality figures"
- "I need to visualize 3D medical imaging data"

**Tool recommendations**:
```
Primary: Hiplot (web-based, comprehensive)
Secondary: FigureYaLLM (for recommendations)
Specialized: 3D Slicer (for medical imaging)
Integration: Export to vector formats for publication
```

### 5. Citation Management & Verification

**When to use**: User needs to manage references, verify citations, or format bibliographies

**Workflow**:
1. Assess citation management needs
2. Recommend citation tools and formats
3. Verify citation accuracy using scripts/verify_citations.py
4. Format references according to journal requirements
5. Check for citation completeness

**Example queries**:
- "Verify all citations in my paper"
- "Format my references in APA style"
- "Check if any citations are missing DOIs"
- "Organize my reference library"

**Tool recommendations**:
```
Primary: Citation verification script (included)
Secondary: K-Dense-AI scientific skills (for advanced management)
Integration: Zotero, Mendeley, or EndNote for library management
```

## Workflow Decision Tree

Use this decision tree to quickly identify the appropriate workflow:

```
User Query
    │
    ├─ Contains "literature", "papers", "search", "review"
    │   └─> Literature Review & Management (Capability 1)
    │
    ├─ Contains "design", "hypothesis", "plan", "methodology"
    │   └─> Research Planning (Capability 2)
    │
    ├─ Contains "write", "draft", "edit", "improve", "polish"
    │   └─> Academic Writing (Capability 3)
    │
    ├─ Contains "visualize", "figure", "chart", "plot", "graph"
    │   └─> Data Visualization (Capability 4)
    │
    ├─ Contains "citation", "reference", "bibliography", "cite"
    │   └─> Citation Management (Capability 5)
    │
    └─ Unclear or multiple aspects
        └─> Ask clarifying questions to determine primary need
```

## Integrated Research Workflows

### Complete Paper Writing Workflow

For users writing a complete research paper:

1. **Literature Review** (Capability 1)
   - Use Biomni to gather relevant papers
   - Use bibliometrix to analyze research landscape
   
2. **Research Planning** (Capability 2)
   - Identify gaps and formulate hypotheses
   - Design methodology
   
3. **Data Analysis & Visualization** (Capability 4)
   - Create figures using Hiplot or specialized tools
   - Ensure publication quality
   
4. **Writing** (Capability 3)
   - Draft with ScholarCopilot
   - Review with PaperDebugger
   - Polish with Academic Writing Assistant
   
5. **Citation Management** (Capability 5)
   - Verify all citations
   - Format references properly

### Systematic Review Workflow

For users conducting systematic reviews:

1. Define search strategy and inclusion criteria
2. Use Biomni + PubMedAI for comprehensive literature search
3. Use bibliometrix for citation network analysis
4. Organize findings with citation management tools
5. Write review using ScholarCopilot
6. Create PRISMA flow diagram using Hiplot

## Tool Selection Guidelines

### By User Expertise Level

**Beginners**:
- Start with: Hiplot (visualization), Academic Writing Assistant (writing)
- Avoid: Complex R packages, command-line tools
- Focus: Web-based tools with GUI

**Intermediate**:
- Recommended: ScholarCopilot, PaperDebugger, bibliometrix
- Can handle: Python scripts, R packages with documentation
- Focus: Integrated workflows

**Advanced**:
- Full toolkit access: All tools including specialized packages
- Can customize: Scripts and workflows
- Focus: Automation and efficiency

### By Research Domain

**Clinical Research**:
- Primary: Biomni, PubMedAI, 3D Slicer
- Focus: Clinical trial data, medical imaging

**Basic Science**:
- Primary: Biomni, Hiplot, bibliometrix
- Focus: Molecular data, pathway visualization

**Epidemiology**:
- Primary: bibliometrix, Hiplot
- Focus: Statistical visualization, meta-analysis

**Translational Research**:
- Primary: Biomni, ScholarCopilot, Hiplot
- Focus: Cross-domain integration


## Resources

This skill includes the following bundled resources:

### scripts/verify_citations.py
Python script for automated citation verification using CrossRef API.

**Usage**:
```bash
python scripts/verify_citations.py <paper_file.md>
```

**Features**:
- Extracts DOIs from text
- Verifies citations against CrossRef database
- Reports invalid or missing citations
- Provides citation metadata (title, authors, year)

### references/tools_catalog.md
Comprehensive catalog of medical research tools with:
- Detailed tool descriptions
- Installation instructions
- Use case recommendations
- Tool selection matrix by expertise level
- Integration workflow examples

Load this reference when users need detailed tool information or when recommending specific tools.

## Example Interactions

### Example 1: Literature Review Request

**User**: "I need to do a literature review on immunotherapy for lung cancer"

**Response**:
1. Clarify scope: "Are you looking for recent papers (last 5 years) or comprehensive historical review?"
2. Assess expertise: "Are you familiar with systematic review methodology?"
3. Recommend tools:
   - **Primary**: Biomni for comprehensive biomedical search
   - **Secondary**: bibliometrix for citation network analysis
4. Provide workflow:
   - Define search terms and inclusion criteria
   - Use Biomni to search PubMed and related databases
   - Export results and analyze with bibliometrix
   - Organize findings by themes
5. Offer next steps: "Would you like help formulating search queries or setting up bibliometrix?"

### Example 2: Paper Writing Assistance

**User**: "Help me write the discussion section of my clinical trial paper"

**Response**:
1. Understand context: "What were your main findings? Do you have the results section drafted?"
2. Recommend tools:
   - **Primary**: ScholarCopilot for AI-assisted writing
   - **Secondary**: PaperDebugger for review
3. Provide structure guidance:
   - Start with summary of key findings
   - Compare with existing literature
   - Discuss limitations
   - Suggest future directions
4. Offer writing support: "I can help draft each subsection. Shall we start with summarizing your key findings?"

### Example 3: Visualization Request

**User**: "I need to create a survival curve for my clinical data"

**Response**:
1. Assess data: "What format is your data in? Do you have time-to-event data with censoring?"
2. Recommend tools:
   - **Primary**: Hiplot for web-based Kaplan-Meier curves
   - **Alternative**: R with survminer package for publication-quality
3. Provide guidance:
   - Prepare data in required format
   - Choose appropriate visualization style
   - Add confidence intervals and p-values
   - Export in publication-ready format
4. Offer assistance: "Would you like help preparing your data or choosing the right plot style?"

## Tips for Effective Use

1. **Be Specific**: The more details you provide about your research task, the better recommendations I can make
2. **Indicate Expertise**: Let me know your technical level so I can recommend appropriate tools
3. **Mention Constraints**: Tell me about time limits, software preferences, or institutional requirements
4. **Ask for Alternatives**: If a recommended tool doesn't work, ask for alternatives
5. **Request Integration**: Ask how to combine multiple tools for comprehensive workflows

## Limitations

- Tool availability may change; always verify GitHub repositories are active
- Some tools require API keys or institutional access
- Installation complexity varies; beginners may need additional support
- Not all tools work on all operating systems
- Some tools are research-grade and may lack polish

## Getting Help

If you encounter issues:
1. Check the tool's GitHub repository for documentation
2. Search existing GitHub issues for solutions
3. Verify you have required dependencies installed
4. Ask me for troubleshooting guidance or alternative tools
