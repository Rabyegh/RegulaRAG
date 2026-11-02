# Project Requirements

> RegulaRAG — AI-Powered Regulatory Intelligence & Compliance Analysis Platform  
> Version: 0.1.0 | Phase: 1 — Foundation

---

## 1. Project Overview

RegulaRAG is an AI-powered platform for regulatory intelligence and compliance analysis. It ingests legal and regulatory documents, processes them using natural language AI models, and enables organisations to search, analyse, and monitor their regulatory obligations across multiple EU frameworks.

The platform combines Retrieval-Augmented Generation (RAG) with a Legal Knowledge Graph to provide citation-grounded answers to regulatory questions and detect legislative changes.

---

## 2. Problem Statement

Organisations operating in the EU must navigate a growing body of complex regulation, including the EU AI Act, GDPR, DSA, DMA, Data Act, and NIS2. Key challenges include:

- **Volume**: Legal documents are lengthy and require expert interpretation.
- **Interconnection**: Regulations cross-reference each other, creating complex obligation webs.
- **Change velocity**: Amendments, implementing acts, and guidance change requirements continuously.
- **Manual effort**: Regulatory analysis today is predominantly manual, slow, and expensive.

There is no AI-native platform purpose-built for EU regulatory intelligence that combines semantic search, citation grounding, and change monitoring in a single system.

---

## 3. Project Objectives

1. Provide accurate, citation-grounded answers to regulatory compliance questions.
2. Enable semantic search across multiple EU regulations simultaneously.
3. Detect and highlight regulatory changes and their compliance impact.
4. Extract and categorise legal obligations applicable to specific contexts.
5. Maintain traceability of every answer to its source regulatory text.
6. Build a maintainable, extensible, and production-ready platform.

---

## 4. Target Users

| User Type | Description |
|-----------|-------------|
| **Compliance Officers** | Track obligations and build compliance programmes |
| **Legal Counsel** | Research regulatory requirements and prepare advice |
| **Policy Analysts** | Monitor legislative changes and cross-regulation impact |
| **Product Managers** | Understand regulatory requirements for product development |
| **Regulatory Affairs Teams** | Respond to regulatory queries and prepare submissions |

---

## 5. Main Use Cases

| ID | Use Case | Description |
|----|----------|-------------|
| UC-001 | Regulatory Question Answering | Ask a specific compliance question and receive a cited answer |
| UC-002 | Cross-Regulation Search | Search a query across multiple EU regulations simultaneously |
| UC-003 | Obligation Extraction | Identify all applicable obligations for a given role or product |
| UC-004 | Regulatory Change Analysis | Compare regulation versions and understand changed obligations |
| UC-005 | Change Monitoring | Receive alerts when regulations relevant to an organisation change |
| UC-006 | Document Ingestion | Ingest new regulatory documents into the knowledge base |
| UC-007 | Compliance Checklist | Generate actionable compliance checklists from regulatory text |

---

## 6. Functional Requirements

### Document Ingestion & Management

| ID | Requirement |
|----|-------------|
| FR-001 | The platform shall support automated ingestion of regulatory documents from authoritative sources. |
| FR-002 | The platform shall preserve and expose document version information (publication date, amendment history). |
| FR-003 | The platform shall validate ingested documents for completeness and structural integrity. |
| FR-004 | The platform shall store raw documents in their original format alongside processed representations. |

### Retrieval & Search

| ID | Requirement |
|----|-------------|
| FR-005 | The platform shall provide hybrid regulatory search combining dense vector retrieval and BM25 lexical matching. |
| FR-006 | The platform shall support cross-encoder reranking of retrieved results. |
| FR-007 | The platform shall support cross-regulation search across all ingested frameworks. |
| FR-008 | The platform shall filter search results by regulation, article, chapter, and recital. |

### Answer Generation

| ID | Requirement |
|----|-------------|
| FR-009 | The platform shall generate answers grounded in retrieved regulatory text with source citations. |
| FR-010 | The platform shall cite specific articles, paragraphs, and recitals in every generated answer. |
| FR-011 | The platform shall clearly indicate uncertainty when the retrieved evidence is insufficient. |
| FR-012 | The platform shall support query decomposition for complex multi-part regulatory questions. |

### Knowledge Graph

| ID | Requirement |
|----|-------------|
| FR-013 | The platform shall maintain a legal knowledge graph capturing entities, definitions, and cross-references. |
| FR-014 | The platform shall support multi-hop reasoning over the knowledge graph. |
| FR-015 | The platform shall identify definitional relationships between terms across regulations. |

### Regulatory Intelligence

| ID | Requirement |
|----|-------------|
| FR-016 | The platform shall detect regulatory changes and compare document versions. |
| FR-017 | The platform shall extract and classify regulatory obligations applicable to specific contexts. |
| FR-018 | The platform shall assess the compliance impact of regulatory changes on extracted obligations. |

### API & Interface

| ID | Requirement |
|----|-------------|
| FR-019 | The platform shall expose a REST API with OpenAPI documentation. |
| FR-020 | The platform shall provide a health check endpoint for operational monitoring. |
| FR-021 | The platform shall provide a web frontend for regulatory research (Phase 8). |

---

## 7. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-001 | **Modularity** — The architecture shall use clearly separated, independently testable modules. | All phases |
| NFR-002 | **Reproducibility** — The development environment shall be fully reproducible using Docker and uv. | Phase 1 |
| NFR-003 | **Configurability** — All application settings shall be configurable via environment variables. | Phase 1 |
| NFR-004 | **Testability** — All modules shall have unit and integration test coverage. | All phases |
| NFR-005 | **Secret security** — No credentials or secrets shall be stored in source control. | Phase 1 |
| NFR-006 | **Traceability** — Every generated answer shall cite traceable regulatory sources. | Phase 4 |
| NFR-007 | **Response latency** — P95 query response time shall not exceed 5 seconds for standard queries. | Phase 4 |
| NFR-008 | **Availability** — The API shall target 99.5% uptime in production deployments. | Phase 8 |
| NFR-009 | **Maintainability** — Code shall follow consistent style enforced by Ruff and type annotations. | Phase 1 |
| NFR-010 | **Observability** — The application shall emit structured logs and metrics. | Phase 7 |

---

## 8. Initial Regulatory Scope

| Regulation | Identifier | Priority |
|-----------|-----------|---------|
| EU AI Act | Regulation (EU) 2024/1689 | High |
| GDPR | Regulation (EU) 2016/679 | High |
| Digital Services Act | Regulation (EU) 2022/2065 | High |
| Digital Markets Act | Regulation (EU) 2022/1925 | Medium |
| Data Act | Regulation (EU) 2023/2854 | Medium |
| NIS2 Directive | Directive (EU) 2022/2555 | Medium |

---

## 9. Technical Constraints

- Python 3.12+ is required for all backend components.
- The backend shall use FastAPI as the web framework.
- Configuration management shall use Pydantic Settings.
- PostgreSQL with pgvector is the primary database.
- Docker and Docker Compose shall be used for all local service dependencies.
- The project management tool shall be uv.
- All code shall pass Ruff lint and format checks.

---

## 10. Security Requirements

| ID | Requirement |
|----|-------------|
| SEC-001 | No credentials shall be stored in source-controlled files. |
| SEC-002 | The `.env` file shall be excluded from Git via `.gitignore`. |
| SEC-003 | Docker containers shall run as non-root users. |
| SEC-004 | API keys and passwords shall be loaded exclusively from environment variables. |
| SEC-005 | All external API keys shall be validated at feature initialisation, not at startup. |
| SEC-006 | The API shall implement authentication and authorisation before exposing sensitive data (Phase 4+). |

---

## 11. Reliability Requirements

- The application shall start cleanly without requiring PostgreSQL, Elasticsearch, or an LLM API key.
- External service connectivity shall be validated lazily when first needed, not at startup.
- All database operations shall use connection pooling.
- Failed LLM calls shall implement retry logic with exponential back-off.

---

## 12. Future Capabilities

The following capabilities are planned for subsequent phases and are explicitly **not** part of Phase 1:

- Document ingestion pipeline (Phase 2)
- Legal document parsing and semantic chunking (Phase 3)
- Vector embeddings and pgvector storage (Phase 3)
- Hybrid RAG engine (Phase 4)
- Cross-encoder reranking (Phase 4)
- LLM-based answer generation (Phase 4)
- Legal Knowledge Graph (Phase 5)
- Regulatory change detection (Phase 6)
- Obligation extraction (Phase 6)
- RAGAS evaluation framework (Phase 7)
- Monitoring and observability (Phase 7)
- React frontend (Phase 8)

---

## 13. Phase 1 Explicit Out-of-Scope

The following items are explicitly **out of scope** for Phase 1:

- Any regulatory document ingestion or storage.
- Any AI model calls or embedding generation.
- Any search or retrieval functionality.
- Any answer generation.
- User authentication and authorisation.
- Frontend implementation.
- Production deployment.
- Database schema migrations.
- Performance testing.
- External API integrations.

