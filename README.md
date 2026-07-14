# FinSight AI

> **Login credentials**: demo account emails and the shared password are in [`AUTH.md`](./AUTH.md) — check there before asking "what are the credentials?"

An AI-powered financial research agent for hedge funds and institutional clients. It analyzes portfolio positions and performance, explains portfolio states and changes, detects the impact of sectoral/policy/global events, and delivers actionable recommendations, real-time monitoring, and alerts through a conversational AI interface.

**Target users**: hedge funds, institutional investors, portfolio managers.

## Tech Stack

- **Backend**: Python (FastAPI), Apache Flink (streaming)
- **Frontend**: Next.js (React)
- **Database**: Azure SQL Server (structured data), ChromaDB (vector embeddings)
- **AI/LLM**: Agentic chat with tool calling (Claude/GPT), MCP (Model Context Protocol) server
- **Infrastructure**: AWS EC2, Azure SQL, Vercel

## Getting Started

See `STARTUP_GUIDE.md` for how to bring up each service (database, ChromaDB, Kafka/Flink, backend, frontend) after a restart.

## More Docs

- `plan.md` — full development plan and phase breakdown
- `status.md` — current project status
- `CLOUD_MIGRATION.md` — local vs. cloud deployment tracker
- `RAG.md` — retrieval-augmented generation / ChromaDB architecture
