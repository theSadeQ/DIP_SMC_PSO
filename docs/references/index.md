# References and Citations

```{toctree}
:maxdepth: 2
:hidden:

bibliography
citation_index
```

This section provides comprehensive citation management and academic references for the DIP_SMC_PSO project.

## Contents

::::{grid} 2
:::{grid-item-card} **Bibliography**
:link: bibliography
:link-type: doc

Complete bibliography with IEEE-style citations and hyperlinked references.
:::

:::{grid-item-card} **Citation Index**
:link: citation_index
:link-type: doc

Organized index of citations by topic and application area.
:::
::::

## Academic Foundation

The DIP_SMC_PSO project builds upon decades of research in nonlinear control theory and optimization. The theoretical foundations draw from several key areas:

### Control Theory Sources

**Sliding Mode Control Fundamentals**
- {cite}`utkin1999sliding` - Foundational work on sliding mode control theory
- {cite}`edwards1998sliding` - Comprehensive treatment of sliding mode systems
- {cite}`shtessel2014sliding` - Modern sliding mode control techniques

**Super-Twisting and Higher-Order SMC**
- {cite}`levant2003higher` - Higher-order sliding mode controllers
- {cite}`moreno2012strict` - Strict Lyapunov functions for super-twisting algorithm
- {cite}`davila2005second` - Second-order sliding mode observers

**Adaptive Control**
- {cite}`slotine1991applied` - Applied nonlinear control fundamentals
- {cite}`krstic1995nonlinear` - Nonlinear and adaptive control design
- {cite}`narendra2012stable` - Stable adaptive systems theory

### Optimization and PSO

**Particle Swarm Optimization**
- {cite}`kennedy1995particle` - Original PSO algorithm
- {cite}`clerc2002particle` - Particle swarm optimization theory
- {cite}`zhang2015comprehensive` - Comprehensive survey of PSO variants

**Multi-objective Optimization**
- {cite}`coello2007evolutionary` - Evolutionary algorithms for multi-objective optimization
- {cite}`deb2001multi` - Multi-objective optimization using evolutionary algorithms

### Inverted Pendulum Systems

**Modeling and Control**
- {cite}`furuta2003swing` - Swing-up and stabilization of inverted pendulum
- {cite}`boubaker2013double` - Double inverted pendulum control techniques
- {cite}`prasad2014double` - Double inverted pendulum modeling approaches

**Experimental Validation**
- {cite}`mills2009control` - Control system implementation for inverted pendulums
- {cite}`wang2011experimental` - Experimental validation of SMC for pendulum systems

## Citation Guidelines

### In-Text Citations

Use the following format for in-text citations:

**Single author:** {cite}`utkin1999sliding` demonstrated that...

**Multiple authors:** According to {cite}`edwards1998sliding`, the sliding mode...

**Multiple references:** Several studies {cite}`levant2003higher,moreno2012strict,davila2005second` have shown...

### Mathematical References

When citing mathematical results, link to both the source and internal equations:

The super-twisting algorithm {cite}`levant2003higher` as implemented in {eq}`eq:supertwisting_law` ensures...

### Code Implementation References

For implementation details, reference both academic sources and code documentation:

The PSO implementation follows {cite}`kennedy1995particle` with modifications described in {doc}`../implementation/api/optimizer`.

## Bibliography Management

### BibTeX Source

All references are maintained in `references/refs.bib` using standard BibTeX format:

```bibtex
@book{utkin1999sliding,
  title={Sliding Mode Control in Electro-Mechanical Systems},
  author={Utkin, Vadim and Guldner, Jürgen and Shi, Jingxin},
  year={1999},
  publisher={CRC Press},
  address={Boca Raton, FL},
  isbn={9780748408269}
}

@article{kennedy1995particle,
  title={Particle Swarm Optimization},
  author={Kennedy, James and Eberhart, Russell},
  journal={Proceedings of IEEE International Conference on Neural Networks},
  volume={4},
  pages={1942--1948},
  year={1995},
  doi={10.1109/ICNN.1995.488968}
}
```

### Citation Validation

The bibliography system includes automatic validation:

- **DOI verification** for journal articles
- **ISBN checking** for books
- **URL accessibility** for web sources
- **Duplicate detection** across bibliography files

## Research Reproducibility

### Code-Citation Mapping

Each implementation module includes explicit citations to theoretical sources:

```python
class SuperTwistingSMC:
    """
    Super-twisting sliding mode controller.

    Based on the algorithm described in {cite}`levant2003higher`
    with finite-time convergence analysis from {cite}`moreno2012strict`.

    References
    ----------
    .. bibliography::
       :filter: key in ["levant2003higher", "moreno2012strict"]
    """
```

### Experimental Reproducibility

All experimental parameters and configurations are documented with literature justification:

```yaml
# Controller parameters based on literature
classical_smc:
  # Sliding surface gain - typical range from {cite}`utkin1999sliding`
  c: 5.0
  # Switching gain - conservative choice per {cite}`edwards1998sliding`
  eta: 1.0
```

## Related Software and Datasets

### Open Source Implementations

- **OpenRAVE** - Robot simulation environment
- **ACADO Toolkit** - Automatic control and dynamic optimization
- **CasADi** - Symbolic framework for nonlinear optimization

### Benchmark Datasets

- **IEEE Control Systems Society** - Standard benchmark problems
- **IFAC Benchmark Collection** - International federation control benchmarks

## Contributing to Bibliography

### Adding New References

1. Add BibTeX entry to appropriate `.bib` file
2. Use consistent citation keys: `firstauthor_year_keyword`
3. Include DOI when available
4. Validate entry using built-in tools

### Citation Style Guide

Follow IEEE citation style:

- **Journal articles:** Author, "Title," *Journal*, vol. X, no. Y, pp. Z-W, Month Year.
- **Books:** Author, *Title*, Edition. Publisher, Year.
- **Conference papers:** Author, "Title," in *Proc. Conference*, City, Year, pp. Z-W.

## Bibliography Statistics

```{list-table} Bibliography Summary
:header-rows: 1
:name: table:bibliography_stats

* - Category
  - Count
  - Percentage
* - Journal Articles
  - 45
  - 60%
* - Conference Papers
  - 20
  - 27%
* - Books
  - 8
  - 11%
* - Technical Reports
  - 2
  - 2%
```

Total references: 75 entries (updated {sub-ref}`today`)

---

**Quick Access:**
- {doc}`bibliography` - Complete reference list
- {doc}`citation_index` - Topical organization
- [BibTeX Source](refs.bib) - Raw bibliography data