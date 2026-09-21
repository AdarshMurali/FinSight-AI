# FinSight AI

> **Login credentials**: demo account emails and the shared password are in [`AUTH.md`](./AUTH.md) — check there before asking "what are the credentials?"

An AI-powered financial research agent for hedge funds and institutional clients. It analyzes portfolio positions and performance, explains portfolio states and changes, detects the impact of sectoral/policy/global events, and delivers actionable recommendations, real-time monitoring, and alerts through a conversational AI interface.

**Target users**: hedge funds, institutional investors, portfolio managers.

## Architecture

- **[`ARCHITECTURE.md`](ARCHITECTURE.md)** — the authoritative technical reference: full tech stack, deployment topology, RAG pipeline, auth model, and CI/CD, with the live-vs-planned status of every component.
- **[`FUNCTIONAL_OVERVIEW.md`](FUNCTIONAL_OVERVIEW.md)** — what the product actually does, feature by feature, including the agentic AI chat tool-calling loop and the always-on risk/alert pipeline.
- **[`docs/architecture/tech-architecture.svg`](docs/architecture/tech-architecture.svg)** — the deployed infrastructure diagram (two AWS EC2 instances, Vercel, Azure SQL, CI/CD).
- **[`docs/architecture/functional-flow.svg`](docs/architecture/functional-flow.svg)** — the agentic chat and monitoring pipelines, diagrammed.

## Tech Stack

- **Backend**: Python (FastAPI), Apache Flink (streaming)
- **Frontend**: Next.js (React)
- **Database**: Azure SQL Server (structured data), ChromaDB (vector embeddings)
- **AI/LLM**: Agentic chat with tool calling (OpenAI `gpt-4o` / `gpt-4o-mini` + `text-embedding-3-small`), MCP (Model Context Protocol) server
- **Infrastructure**: AWS EC2, Azure SQL, Vercel

## Getting Started

See `STARTUP_GUIDE.md` for how to bring up each service (database, ChromaDB, Kafka/Flink, backend, frontend) after a restart.

## More Docs

- `plan.md` — full development plan and phase breakdown
- `status.md` — current project status
- `CLOUD_MIGRATION.md` — local vs. cloud deployment tracker
- `RAG.md` — retrieval-augmented generation / ChromaDB architecture
