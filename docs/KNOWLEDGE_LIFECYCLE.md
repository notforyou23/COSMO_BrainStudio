# The Knowledge Lifecycle: Workspaces vs. Releases

This document memorializes the core philosophy behind the COSMO Brain Platform: turning raw research into durable, versioned knowledge.

## 🔬 The Workflow: From "Process" to "Product"

In the COSMO ecosystem, intelligence exists in two distinct states that parallel the software development lifecycle.

### 1. The Research Workspace: "Work in Progress"
A **Workspace** (traditionally a COSMO Run) is a live, high-entropy environment. It is where agents are actively reasoning, failing, scratching out ideas, and generating massive amounts of telemetry.
- **Analogy**: A local development branch with all its `.build` files, temp data, and debug logs.
- **Content**: Agent logs, thought streams, intermediate scratch files, raw telemetry.
- **Size**: Large (500MB – 2GB+).
- **Goal**: Discovery and active computation.

### 2. The Published Brain: "Stable Release"
A **.brain** package is the result of the "Publishing" process. It is a refined, high-density artifact designed for portability and consumption.
- **Analogy**: A tagged production release or a packaged binary.
- **Content**: The final Knowledge Graph, curated insights, high-fidelity deliverables, and a standardized manifest.
- **Size**: Lightweight (10MB – 50MB).
- **Goal**: Distribution, sharing, forking, and archival.

---

## 🚀 Why We Publish Versions

If we can already see "Workspaces" in the Browser, why bother publishing a .brain?

### 1. The Signal-to-Noise Filter
The publishing process acts as a **distillation filter**. It strips away the gigabytes of agent noise and failed intermediate steps, leaving only the "Intelligence" that was actually verified and connected to the knowledge graph.

### 2. True Portability
A Workspace is often tied to the specific machine and environment where it was created. A **Published Brain** is self-contained. It uses relative paths and standardized schemas that allow it to be launched on any server in seconds.

### 3. The "GitHub for Brains" Vision
Just as GitHub uses the `.git` folder to understand how to merge code, the Brain Platform uses the `.brain` manifest to understand how to **merge intelligence**. 
- You research in COSMO (The Studio).
- You review in the Workspace (The Rough Mix).
- You publish as a .brain (The Mastered Track).

## 🗺️ Vision Statement
We believe that AI research shouldn't be trapped in ephemeral chat logs. By **publishing** knowledge into portable artifacts, we make human-AI intelligence compound over time.

---
*Memorialized Dec 2025 | Powered by [cosmo.evobrew.com](https://cosmo.evobrew.com)*
