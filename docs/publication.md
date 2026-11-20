# Publication and release guidance

## Repository scope

Suggested repository name: `idss-toolkit`. Publish the repository only after author review. The package implements manuscript equations (12)-(17) and the four weight profiles; the generalized K-criterion extension is not implemented in version 0.2.0. Describe it as an implementation or toolkit, rather than a new scoring method or a complete reproduction of all experiments.

Before public release, confirm the license with the authors, replace demo metadata, add the measured inputs behind Table 7 if redistribution is appropriate, run the tests in the intended Python environments and verify those inputs against the manuscript. Model and dataset files need not be included. The package's existing GitHub Actions file is a starting CI configuration; local checks do not establish that GitHub-hosted CI has run.

## Manuscript wording after the repository is public

Use this statement only once the repository is public and the URL works:

> A reusable implementation of IDSS, including validation-based scoring, configurable criterion weights, weight-sensitivity analysis and usage examples, is available at [repository URL].

The statement belongs at the end of Section 3.8, with a matching entry in the Data Availability Statement. Do not claim that the processed datasets, HPO notebooks or trained models are publicly available unless they are actually released. Any existing reasonable-request statement can remain for those other artifacts.

## Stable citation

Tag a verified release, record its version and exact commit, and consider archiving the release in an archival repository. Add a DOI only after one is actually issued. The included `CITATION.cff` describes the software. Add the public repository URL and final manuscript bibliographic details when available; do not insert placeholder DOIs or acceptance claims.

## Next development steps

Potential extensions include adapters for existing experiment exports, a checked manuscript reproduction example using unrounded input records, platform winner comparison, broader weight-grid analysis and an interactive viewer. Keep them separate from the implemented v0.2.0 features.
