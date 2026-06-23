---
title: "Colab deploy: agentes/ module bootstrap via self-clone"
type: concept
created: 2026-06-22
updated: 2026-06-22
sources: ["lumina_bg.ipynb"]
tags: [concept, colab, deploy, bootstrap, packaging]
---

# Colab deploy: agentes/ module bootstrap via self-clone

Cell 7 of [[entities/deploy-colab-notebook]] makes the `agentes/` Python package available inside Colab at runtime by cloning the project's own GitHub repository.

## The bootstrap sequence

```python
REPO_DIR = "/content/lumina-bg"
if os.path.exists(f"{REPO_DIR}/agentes"):
    sys.path.insert(0, REPO_DIR)
elif os.path.exists("/content/agentes"):
    sys.path.insert(0, "/content")
else:
    subprocess.run([
        "git", "clone", "--depth", "1",
        "https://github.com/rob-d3v/background-magic-free",
        REPO_DIR
    ], check=False)
    if os.path.exists(f"{REPO_DIR}/agentes"):
        sys.path.insert(0, REPO_DIR)
    else:
        raise RuntimeError("Nao foi possivel encontrar os modulos agentes/. ...")
```

## Why self-cloning

The notebook is distributed as a standalone `.ipynb` file (direct download or Colab link). Users do not clone the repository manually. The `agentes/` package (`extracao.py`, `remocao.py`, `geracao_fundo.py`, `relighting.py`, `exportacao.py`) must be importable at runtime. Self-cloning avoids requiring users to install any package via pip or upload files manually.

## Priority order

1. `/content/lumina-bg/agentes/` — repo already cloned in a previous cell run.
2. `/content/agentes/` — developer has the package in the Colab working dir (manual override).
3. Clone from GitHub — the normal first-run path.

## Consequence: code in notebook vs. code in repo

The notebook delegates all pipeline logic to the `agentes/` modules from the repo. The notebook cells themselves contain only orchestration glue (paths, params, drive mount, progress printing). This means:
- Bug fixes in `agentes/*.py` are picked up automatically on the next Colab run (no notebook update needed).
- The notebook version and the repo version must stay compatible; a breaking change to `agentes/` public function signatures would break existing notebook users.

## Alternative not used: packaging as pip install

Installing `agentes/` as a pip package would avoid the clone but would require versioned releases and a PyPI or VCS-based `pip install`. Self-clone is simpler for the current single-developer project.

## Related

[[entities/deploy-colab-notebook]] · [[concepts/deploy-colab-cell-data-flow]] · [[decisions/deploy-colab-primary-gpu-path]] · [[index]]
