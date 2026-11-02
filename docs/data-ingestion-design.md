# Regulatory Data Ingestion Pipeline Design

> **RegulaRAG — AI-Powered Regulatory Intelligence & Compliance Analysis Platform**  
> **Subphase:** Phase 2, Subphase 2.1  
> **Design Status:** Approved Architectural Specification  
> **Authoritative Source:** EUR-Lex (Publications Office of the European Union)

---

## 1. Executive Summary & Design Principles

The RegulaRAG ingestion pipeline is responsible for acquiring authoritative legal documents, validating their cryptographic and structural integrity, and storing immutable raw artifacts alongside structured metadata.

### Core Architectural Principles
1. **Source Authenticity:** All regulatory texts must originate directly from official institutional repositories (primarily EUR-Lex). Unofficial secondary sites are prohibited.
2. **Immutability of Raw Artifacts:** The original downloaded document (HTML, XML, or PDF) is stored unchanged. Downstream parsing, chunking, or cleaning must never mutate the raw artifact.
3. **Deterministic Storage:** Every stored file follows a predictable, reproducible directory and naming convention.
4. **Cryptographic Traceability:** Every artifact is fingerprinted with a SHA-256 checksum upon acquisition to guarantee provenance and detect tampering.
5. **Strict Version & Category Segregation:** Original legal acts, consolidated syntheses, corrigenda, and amending acts must be cleanly categorized and never conflated.

---

## 2. Regulatory Document Ingestion Lifecycle

The ingestion workflow proceeds through nine discrete, deterministic stages:

```mermaid
flowchart TD
    S1["1. Source Discovery\n(Registry Lookup / EUR-Lex Query)"]
    S2["2. Metadata Retrieval\n(HTTP HEAD / SPARQL / Cellar API)"]
    S3["3. Duplicate & Change Detection\n(Conditional Check / ETag / Checksum)"]
    S4["4. Document Acquisition\n(Streaming HTTP GET with Backoff)"]
    S5["5. Raw Artifact Preservation\n(Atomic Write to data/raw/...)"]
    S6["6. Content & Format Validation\n(MIME type / Well-formedness check)"]
    S7["7. Version & Instrument Classification\n(Original act vs. Consolidated vs. Corrigendum)"]
    S8["8. Metadata Sidecar Persistence\n(Write .meta.json sidecar)"]
    S9["9. Downstream Processing Handoff\n(Queue / Event for Phase 3 Chunking)"]

    S1 --> S2 --> S3
    S3 -- "Unchanged (304 / Checksum match)" --> SKIP["No-op (Skip Download, Update Verified Timestamp)"]
    S3 -- "New / Updated" --> S4 --> S5 --> S6 --> S7 --> S8 --> S9
```

### Detailed Lifecycle Stages

1. **Source Discovery:**
   - Evaluates target document requests against `configs/regulatory_sources.yaml`.
   - Resolves target CELEX identifier, official EUR-Lex URL, and preferred format.
2. **Metadata Retrieval:**
   - Performs conditional metadata queries (HTTP `HEAD` request or EUR-Lex Cellar/SPARQL metadata lookup).
   - Collects `Content-Length`, `Content-Type`, `ETag`, and `Last-Modified` headers.
3. **Duplicate & Change Detection:**
   - Checks local storage for matching `(document_id, version, format)` tuples.
   - Evaluates conditional headers (`If-None-Match`, `If-Modified-Since`).
   - If unchanged, marks the registry verified timestamp and skips redundant download.
4. **Document Acquisition:**
   - Executes streaming HTTP GET using an asynchronous client with rate-limiting and connection pooling.
   - Applies exponential backoff with jitter on transient network/server errors (500, 502, 503, 504, 429).
5. **Raw Artifact Preservation:**
   - Downloads into a temporary file (`.part`), computes the SHA-256 hash incrementally, and renames atomically to the target filename upon completion.
6. **Content & Format Validation:**
   - Verifies the downloaded file exceeds minimum size thresholds (>1 KB).
   - Validates format headers (e.g., HTML contains `<!DOCTYPE html>` or `<html>`, XML is well-formed, PDF starts with `%PDF-`).
7. **Version & Instrument Classification:**
   - Identifies whether the artifact represents a base act (Sector 3), an official corrigendum (`R(xx)`), or an editorial consolidation (Sector 0).
8. **Metadata Sidecar Persistence:**
   - Emits an immutable JSON sidecar (`.meta.json`) adjacent to the downloaded artifact.
9. **Downstream Processing Handoff:**
   - Signals availability of the validated artifact for structural parsing and legal-aware semantic chunking (Phase 3).

---

## 3. Ingestion Metadata Contract

Every acquired document artifact produces an immutable metadata sidecar conforming to the schema below:

```json
{
  "$schema": "https://regularag.org/schemas/v1/artifact_metadata.json",
  "artifact_id": "art_32024R1689_oj_en_html_v20240712",
  "document_id": "eu_ai_act",
  "name": "Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13 June 2024 laying down harmonised rules on artificial intelligence...",
  "abbreviation": "EU AI Act",
  "instrument_type": "Regulation",
  "celex_id": "32024R1689",
  "eli_uri": "http://data.europa.eu/eli/reg/2024/1689/oj",
  "jurisdiction": "EU",
  "source_authority": "European Parliament and Council of the European Union",
  "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689",
  "language": "EN",
  "document_category": "original_act",
  "is_consolidated": false,
  "consolidation_date": null,
  "is_corrigendum": false,
  "corrigendum_parent_celex": null,
  "publication_date": "2024-07-12",
  "entry_into_force_date": "2024-08-01",
  "application_date": "2026-08-02",
  "transposition_deadline": null,
  "acquisition": {
    "retrieved_at": "2026-11-02T20:15:30.123456Z",
    "http_status": 200,
    "etag": "\"12345-abcdef67890\"",
    "last_modified_header": "Fri, 12 Jul 2024 07:00:00 GMT",
    "retrieval_duration_seconds": 1.42
  },
  "file_metadata": {
    "format": "HTML",
    "media_type": "text/html",
    "file_size_bytes": 1845230,
    "sha256_checksum": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    "storage_relpath": "data/raw/eu/eu_ai_act/2024-07-12/eu_ai_act_32024R1689_original.html",
    "sidecar_relpath": "data/raw/eu/eu_ai_act/2024-07-12/eu_ai_act_32024R1689_original.meta.json"
  },
  "validation": {
    "is_valid": true,
    "validated_at": "2026-11-02T20:15:31.000000Z",
    "validation_checks_passed": [
      "size_greater_than_1kb",
      "html_well_formed_root",
      "sha256_verified"
    ]
  }
}
```

---

## 4. Distinguishing Document Categories and Update Events

In regulatory compliance, misidentifying document status creates severe legal risks. The pipeline enforces unambiguous classification rules:

| Category | CELEX Pattern | Legally Binding? | Update Trigger / Description |
|---|---|---|---|
| **Original Legal Act** | `3YYYY[R/L]NNNN` | **Yes (Authentic)** | Published in the Official Journal (OJ). The baseline legal act. |
| **Consolidated Text** | `0YYYY[R/L]NNNN-YYYYMMDD` | **No (Editorial synthesis)** | Published periodically by the Publications Office when amendments or corrigenda take effect. Suffix denotes the effective date. |
| **Amending Legal Act** | Distinct CELEX (e.g., `32024R...`) | **Yes (Authentic)** | A separate regulation or directive enacted by legislators to formally modify specific articles of an existing act. |
| **Corrigendum (Correction)** | `3YYYY[R/L]NNNNR(XX)` | **Yes (Authentic)** | An official correction rectifying linguistic or typographical errors across OJ editions. |
| **Unchanged Retrieval** | Identical SHA-256 | N/A | Document was queried again, but remote ETag or SHA-256 matches existing local artifact. Zero processing needed. |

---

## 5. Raw Data Storage Architecture

### Directory Layout
Storage is structured deterministically by jurisdiction, document identifier, and effective version:

```
data/raw/
└── {jurisdiction}/
    └── {document_id}/
        ├── original_{publication_date}/
        │   ├── {document_id}_{celex}_original.html
        │   ├── {document_id}_{celex}_original.meta.json
        │   └── {document_id}_{celex}_original.pdf (optional secondary format)
        ├── corrigenda/
        │   └── {corrigendum_celex}/
        │       ├── {document_id}_{corrigendum_celex}.html
        │       └── {document_id}_{corrigendum_celex}.meta.json
        └── consolidated_{consolidation_date}/
            ├── {document_id}_{consolidated_celex}.html
            └── {document_id}_{consolidated_celex}.meta.json
```

### Example Structure for GDPR:
```
data/raw/
└── eu/
    └── eu_gdpr/
        ├── original_2016-05-04/
        │   ├── eu_gdpr_32016R0679_original.html
        │   └── eu_gdpr_32016R0679_original.meta.json
        ├── corrigenda/
        │   ├── 32016R0679R02/
        │   │   ├── eu_gdpr_32016R0679R02.html
        │   │   └── eu_gdpr_32016R0679R02.meta.json
        │   └── 32016R0679R03/
        │       ├── eu_gdpr_32016R0679R03.html
        │       └── eu_gdpr_32016R0679R03.meta.json
        └── consolidated_2021-03-04/
            ├── eu_gdpr_02016R0679-20210304.html
            └── eu_gdpr_02016R0679-20210304.meta.json
```

### Safety and Atomicity Rules
- **Atomic Writes:** Downloads write to `filename.tmp.[uuid]` and are renamed only when the stream completes and SHA-256 calculation matches.
- **Fail-Safe Cleanup:** If a download fails or is aborted, the `.tmp` file is immediately deleted.
- **Read-Only Downstream Operations:** Future ingestion and parsing components mount `data/raw` with read-only access.

---

## 6. Update Detection Strategy

To prevent redundant downloads and network saturation, the pipeline uses a layered detection hierarchy:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. HTTP HEAD with Conditional Headers                       │
│    (If-None-Match, If-Modified-Since)                       │
│    Fastest check — 304 Not Modified stops execution         │
├─────────────────────────────────────────────────────────────┤
│ 2. EUR-Lex Cellar SPARQL Metadata Query                     │
│    Checks for newly linked corrigenda or consolidated acts   │
├─────────────────────────────────────────────────────────────┤
│ 3. Incremental Content SHA-256 Checksum                      │
│    Authoritative proof of byte-for-byte change              │
└─────────────────────────────────────────────────────────────┘
```

- **Authoritative:** SHA-256 hash computation and EUR-Lex official OJ publication notices.
- **Optimization Hints:** HTTP `ETag` and `Last-Modified` headers. If the server does not support conditional headers, the file is downloaded to temporary storage and evaluated by hash before writing to permanent storage.

---

## 7. Reliability, Rate Limiting, and Error Handling

### HTTP Client Policies
- **User Agent:** `RegulaRAG-Bot/0.1.0 (+https://github.com/Rabyegh/RegulaRAG; compliance-research)`
- **Polite Crawling Rate:** Maximum 1 request per second to EUR-Lex endpoints.
- **Connection Timeout:** 10 seconds.
- **Read Timeout:** 60 seconds (accommodates large regulatory documents up to 5 MB).
- **Concurrency:** Maximum 2 concurrent connections per domain.

### Fault Matrix and Mitigation

| Error Scenario | HTTP Status | Handling Strategy |
|---|---|---|
| Rate limited | 429 Too Many Requests | Obey `Retry-After` header if present; otherwise apply exponential backoff (initial delay: 5s, multiplier: 2.0, max: 60s). |
| Server unavailable | 502 / 503 / 504 | Up to 3 retries with jittered exponential backoff. |
| Document not found | 404 Not Found | Mark source entry as `failed_discovery`; do not retry automatically; log warning with CELEX and URL for review. |
| Incomplete stream | Network disconnect | Discard `.tmp` file; increment retry counter; log socket error. |
| Malformed content | Content validation failure | Flag artifact as `corrupted`; quarantine file to `data/quarantine/`; notify pipeline monitor. |

