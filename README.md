# 🧠 COSMO Brain Platform

> **The Standalone Explorer for Synthetic Intelligence.**

COSMO Brain Platform is a portable, high-performance environment designed to host, query, and extend research artifacts produced by the COSMO Autonomous Research System. It brings the power of persistent, compound intelligence to a standalone, deployable package. 

## 🚀 Key Features

*   **Brain Browser**: A visual library for discovering and launching `.brain` knowledge packages.
*   **Knowledge Query**: High-fidelity synthesis engine powered by GPT-5.2 for deep knowledge graph interrogation.
*   **AI-Augmented IDE**: A full Cursor-style web environment for collaborative document editing and research extension.
*   **Graph Exploration**: Interactive visualization of complex memory networks and concept entanglements.

## 📦 Included Showcase Brains

This repository includes several pre-crystallized research artifacts in the `brains/` directory:
*   **Art and Music**: A dense knowledge graph (5,000+ edges) covering the history of human expression and aesthetics.
*   **Mathematics**: Advanced modeling across algebra, calculus, geometry, and probability.
*   **Physics**: Comprehensive research into fundamental physical laws and dynamics.

## 🛠️ Quick Start

```bash
# 1. Setup the environment
./setup.sh

# 2. Add your API Keys
# Edit the generated .env file

# 3. Launch the Platform
npm start
```
Browser available at: `http://localhost:3398`

## 📁 Repository Structure

```
COSMO_BrainStudio/
├── index.js            # Unified Launcher (npm start)
├── README.md           # Documentation & Security Guide
├── .env.example        # Template for API keys
├── .gitignore          # Protection for sensitive files
├── brains/             # Included example .brain packages
├── server/             # Refactored Browser and Studio servers
├── lib/                # Standalone AI and Query logic
└── public/             # Full IDE and Browser frontend
```

## 🔒 Security & Safety

Built for **Trusted Local Environments**:
*   **Local-First**: No research data is uploaded; the IDE operates strictly on your local disk.
*   **Isolated Spawning**: Each Brain Studio instance runs in its own process.
*   **Terminal Gating**: The AI can execute terminal commands to assist in research. Always review proposed actions in the "AI Edits" panel.

---
*COSMO Brain Platform v2.1 | Powered by [cosmo.evobrew.com](https://cosmo.evobrew.com)* .peace.
