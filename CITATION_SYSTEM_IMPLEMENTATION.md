# Citation System Implementation Plan

## Overview

Implementation of a comprehensive citation and bibliography system for the DIP_SMC_PSO documentation, based on ChatGPT's analysis and the existing strategy in CLAUDE.md.

## Source Analysis

**Analyzed ChatGPT Implementation:**
- Location: `D:\Projects\main\chatgpt_analysis_files\task1_citation_bibliography_system\chatgpt final task 1\`
- Complete Sphinx-based citation system with `sphinxcontrib-bibtex`
- Topical bibliography organization (SMC, PSO, DIP, Software)
- Citation mapping from numbered `[1]-[8]` to semantic keys
- Example RST documentation with proper citations

## Implementation Strategy

### 1. Bibliography Organization (Hybrid Topical → Alphabetical)

**Directory Structure:**
```
docs/
  bib/
    smc.bib         # Sliding-mode control & nonlinear control refs
    pso.bib         # PSO and related optimization refs
    dip.bib         # Inverted-pendulum / system modeling refs
    software.bib    # Packages, toolboxes, datasets
```

### 2. Key Technologies & Configuration

**Sphinx Extensions Required:**
- `sphinxcontrib.bibtex` for bibliography support
- Numeric citation style matching existing `[1]` format
- Multiple .bib file loading capability

**Configuration Updates for `docs/conf.py`:**
```python
extensions = [
    # ... existing extensions
    "sphinxcontrib.bibtex",
]

bibtex_bibfiles = [
    "bib/smc.bib",
    "bib/pso.bib",
    "bib/dip.bib",
    "bib/software.bib",
]
bibtex_default_style = "unsrt"          # stable ordering
bibtex_reference_style = "label"        # renders [1], [2], ...
bibtex_tooltips = True
bibtex_bibliography_header = ".. rubric:: References"
```

### 3. Citation Key Naming Convention

**Pattern:** `topic_authorYear_shortTitle` (snake_case, ASCII)

**Topics:**
- `smc` - Sliding Mode Control
- `pso` - Particle Swarm Optimization
- `dip` - Double Inverted Pendulum systems
- `soft` - Software/tooling references

**Examples:**
- `smc_slotine_li_1991_applied_nonlinear_control`
- `pso_kennedy_1995_particle_swarm_optimization`
- `dip_khalil_2002_nonlinear_systems`
- `soft_numpy_2024_fundamental_package`

### 4. Citation Mapping (Existing [1]-[8] to Keys)

**From ChatGPT's `citation_map.json`:**
```json
{
  "1": "dip_khalil_2002_nonlinear_systems",
  "2": "dip_khalil_2002_nonlinear_systems",
  "3": "smc_utkin_2013_sliding_mode_control",
  "4": "smc_slotine_li_1991_applied_nonlinear_control",
  "5": "smc_slotine_li_1991_applied_nonlinear_control",
  "6": "smc_levant_2003_higher_order_smc",
  "7": "smc_shtessel_2014_sliding_mode_control_and_observation",
  "8": "dip_khalil_2002_nonlinear_systems"
}
```

### 5. Key Bibliography Entries

**SMC Theory (`smc.bib`):**
- Slotine & Li (1991) - Applied Nonlinear Control
- Utkin et al. (2013) - Sliding Mode Control in Engineering
- Levant (2003) - Higher-order sliding modes
- Shtessel et al. (2014) - Sliding Mode Control and Observation

**PSO Optimization (`pso.bib`):**
- Kennedy & Eberhart (1995) - Original PSO paper
- Recent PSO reviews and applications

**DIP Systems (`dip.bib`):**
- Khalil (2002) - Nonlinear Systems textbook
- DIP-specific control strategy papers

**Software (`software.bib`):**
- NumPy, SciPy, Matplotlib citations
- Numerical methods for stiff ODEs

### 6. Usage Pattern

**In RST files:**
```rst
Text with citation :cite:`smc_slotine_li_1991_applied_nonlinear_control`.

.. rubric:: References
.. bibliography::
```

**Replacement Process:**
- Replace `\[([1-9]\d*)\]` with `:cite:`KEY`` using mapping
- Add `.. bibliography::` sections to pages with citations

## Implementation Tasks

### ✅ Completed
1. Examine ChatGPT's citation system implementation files
2. Read and analyze the bibliography structure and configuration

### 🔄 In Progress
3. Create docs/bib/ directory structure in current project

### ⏳ Pending
4. Copy and adapt bibliography files (smc.bib, pso.bib, dip.bib, software.bib)
5. Update docs/conf.py with sphinxcontrib-bibtex configuration
6. Implement citation mapping system and replace numbered citations
7. Add bibliography sections to existing documentation pages
8. Test and validate the citation system builds correctly

## Files to Process

**Documentation files with numbered citations:**
- Check existing `.rst` files in `docs/` for `[1]`-`[8]` patterns
- Verify current `docs/conf.py` configuration
- Identify pages needing bibliography sections

**Dependencies:**
- Ensure `sphinxcontrib-bibtex` is in requirements
- Test build system compatibility

## Quality Standards

**BibTeX Entry Requirements:**
- Correct entry types (@book, @article, @inproceedings, @software)
- Complete metadata (author, title, year, publisher/journal, DOI/URL)
- Consistent formatting and normalization
- ASCII-safe keys following convention

**Integration Testing:**
- Build docs with `-W` (warnings as errors)
- Verify all citations resolve correctly
- Check bibliography rendering quality
- Validate cross-references and links

## Next Steps

1. **Create directory structure** and copy bibliography files
2. **Update Sphinx configuration** with bibtex settings
3. **Implement citation replacement** using mapping file
4. **Add bibliography sections** to documentation pages
5. **Test complete build pipeline** and validate output

---

**File:** `CITATION_SYSTEM_IMPLEMENTATION.md`
**Created:** 2025-09-20
**Purpose:** Implementation roadmap for comprehensive citation system based on ChatGPT analysis