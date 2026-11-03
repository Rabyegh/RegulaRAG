# Official Regulatory Source Catalog

> **RegulaRAG — AI-Powered Regulatory Intelligence & Compliance Analysis Platform**  
> **Catalog Version:** 1.0.0 | **Verification Date:** 2026-11-02  
> **Authoritative Source:** EUR-Lex (Publications Office of the European Union)

---

## 1. Overview & Research Methodology

RegulaRAG grounds all compliance and regulatory intelligence in **primary, authentic legal texts** published by the European Union. In legal informatics, reliance on unofficial third-party repositories introduces critical risks, including missing corrigenda, unannounced editorial omissions, or mislabeled consolidated versions.

### Authoritative Hierarchy of EU Law

Under EU legal doctrine, documents published in the **Official Journal of the European Union (OJ)** constitute the sole authentic legal acts:

```
┌─────────────────────────────────────────────────────────────┐
│                       EU Treaties                           │
│                 (Primary Legislation)                       │
├─────────────────────────────────────────────────────────────┤
│             Regulations, Directives, Decisions              │
│       (Secondary Legislation — Sector 3 in CELEX)           │
│                   AUTHENTIC LEGAL TEXT                      │
├─────────────────────────────────────────────────────────────┤
│               Delegated & Implementing Acts                 │
│               (Technical Standards & Rules)                 │
├─────────────────────────────────────────────────────────────┤
│                    Consolidated Texts                       │
│        (Sector 0 in CELEX — Editorial, Non-Binding)          │
└─────────────────────────────────────────────────────────────┘
```

### Critical Legal Distinctions

1. **Original Legal Act (Sector 3):** The authentic legislative text as voted by the European Parliament and Council and published in the Official Journal. It is legally binding.
2. **Consolidated Text (Sector 0):** An editorial synthesis prepared by the Publications Office that integrates the original act and subsequent amendments or corrigenda into a single reading text. **Consolidated texts have no legal value**; in legal proceedings, only the original act and amending acts published in the OJ may be cited.
3. **Corrigenda (Corrections):** Official notices published in the OJ to fix translation errors, numerical typos, or discrepancies among the 24 official EU language versions.
4. **Regulation vs. Directive:**
   - **Regulation:** Directly applicable in its entirety across all EU Member States from its date of application without requiring national transposition.
   - **Directive:** Binding as to the result to be achieved, but leaves the choice of form and methods to Member States. Directives require national transposition laws by a mandatory **transposition deadline**.

---

## 2. Six-Document Regulatory Scope

| # | Regulation / Directive | Instrument | CELEX Identifier | ELI URI | OJ Citation | Legal Status |
|---|------------------------|------------|------------------|---------|-------------|--------------|
| 1 | **EU AI Act** | Regulation | `32024R1689` | [eli/reg/2024/1689/oj](http://data.europa.eu/eli/reg/2024/1689/oj) | OJ L, 2024/1689, 12.7.2024 | In force (phased application) |
| 2 | **GDPR** | Regulation | `32016R0679` | [eli/reg/2016/679/oj](http://data.europa.eu/eli/reg/2016/679/oj) | OJ L 119, 4.5.2016, p. 1–88 | In force (fully applicable) |
| 3 | **Digital Services Act (DSA)** | Regulation | `32022R2065` | [eli/reg/2022/2065/oj](http://data.europa.eu/eli/reg/2022/2065/oj) | OJ L 277, 27.10.2022, p. 1–102 | In force (fully applicable) |
| 4 | **Digital Markets Act (DMA)** | Regulation | `32022R1925` | [eli/reg/2022/1925/oj](http://data.europa.eu/eli/reg/2022/1925/oj) | OJ L 265, 12.10.2022, p. 1–66 | In force (fully applicable) |
| 5 | **Data Act** | Regulation | `32023R2854` | [eli/reg/2023/2854/oj](http://data.europa.eu/eli/reg/2023/2854/oj) | OJ L, 2023/2854, 22.12.2023 | In force (application: 2025-09-12) |
| 6 | **NIS2 Directive** | Directive | `32022L2555` | [eli/dir/2022/2555/oj](http://data.europa.eu/eli/dir/2022/2555/oj) | OJ L 333, 27.12.2022, p. 80–152 | In force (transposition expired) |

---

## 3. Detailed Document Profiles

### 3.1 EU AI Act — Regulation (EU) 2024/1689

- **Full Title:** Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13 June 2024 laying down harmonised rules on artificial intelligence and amending Regulations (EC) No 300/2008, (EU) No 167/2013, (EU) No 168/2013, (EU) 2018/858, (EU) 2018/1139 and (EU) 2019/2144 and Directives 2014/90/EU, (EU) 2016/797 and (EU) 2020/1828 (Artificial Intelligence Act)
- **Common Abbreviation:** EU AI Act (AIA)
- **Legal Instrument:** Regulation (directly applicable)
- **CELEX Number:** `32024R1689`
  - `3`: Sector 3 (Secondary legislation)
  - `2024`: Year of adoption
  - `R`: Regulation
  - `1689`: Document number
- **ELI Identifier:** `http://data.europa.eu/eli/reg/2024/1689/oj`
- **Official EUR-Lex URL:** `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689`
- **Publication Date:** 12 July 2024
- **Entry into Force:** 1 August 2024 (20th day following publication)
- **General Application Date:** 2 August 2026 (24 months after entry into force)
- **Staggered Application Milestones:**
  - *2 February 2025:* Prohibited AI practices take effect (Article 111(2)).
  - *2 August 2025:* Obligations for General-Purpose AI (GPAI) models, governance bodies, and penalties take effect (Article 111(2)).
  - *2 August 2026:* General rules and Annex III high-risk AI system obligations take effect (Article 111(1)).
  - *2 August 2027:* Obligations for high-risk AI systems embedded in Annex I harmonised products take effect (Article 111(3)).
- **Transposition Deadline:** `null` (Regulation)
- **Corrigenda:**
  - `32024R1689R(01)`: Corrigendum published in OJ L on 20 November 2024 rectifying cross-references and linguistic nuances.
- **Consolidated Version:** None published yet by the Publications Office.
- **Available Formats on EUR-Lex:** HTML, XML (Formex / AKN), PDF.

---

### 3.2 GDPR — Regulation (EU) 2016/679

- **Full Title:** Regulation (EU) 2016/679 of the European Parliament and of the Council of 27 April 2016 on the protection of natural persons with regard to the processing of personal data and on the free movement of such data, and repealing Directive 95/46/EC (General Data Protection Regulation)
- **Common Abbreviation:** GDPR
- **Legal Instrument:** Regulation (directly applicable)
- **CELEX Number:** `32016R0679`
- **ELI Identifier:** `http://data.europa.eu/eli/reg/2016/679/oj`
- **Official EUR-Lex URL:** `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679`
- **Publication Date:** 4 May 2016
- **Entry into Force:** 24 May 2016 (20th day following publication)
- **Application Date:** 25 May 2018 (Article 99(2))
- **Transposition Deadline:** `null` (Regulation)
- **Corrigenda:**
  - `32016R0679R(02)`: Published in OJ L 127, 23.5.2018, p. 2 (correcting Article 37(1)(c) and linguistic discrepancies).
  - `32016R0679R(03)`: Published in OJ L 74, 4.3.2021, p. 35 (correcting cross-references).
- **Consolidated Version:**
  - CELEX `02016R0679-20210304`
  - ELI: `http://data.europa.eu/eli/reg/2016/679/2021-03-04`
  - Synthesizes the original act and both corrigenda.
- **Available Formats on EUR-Lex:** HTML, XML, PDF.

---

### 3.3 Digital Services Act (DSA) — Regulation (EU) 2022/2065

- **Full Title:** Regulation (EU) 2022/2065 of the European Parliament and of the Council of 19 October 2022 on a Single Market For Digital Services and amending Directive 2000/31/EC (Digital Services Act)
- **Common Abbreviation:** DSA
- **Legal Instrument:** Regulation (directly applicable)
- **CELEX Number:** `32022R2065`
- **ELI Identifier:** `http://data.europa.eu/eli/reg/2022/2065/oj`
- **Official EUR-Lex URL:** `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2065`
- **Publication Date:** 27 October 2022
- **Entry into Force:** 16 November 2022
- **General Application Date:** 17 February 2024
- **Staggered Milestones:** Very Large Online Platforms (VLOPs) and Very Large Online Search Engines (VLOSEs) were subject to obligations 4 months after their designation by the Commission (from August 2023 onward).
- **Transposition Deadline:** `null` (Regulation)
- **Corrigenda:** None currently published.
- **Consolidated Version:** No consolidated edition yet published.
- **Available Formats on EUR-Lex:** HTML, XML, PDF.

---

### 3.4 Digital Markets Act (DMA) — Regulation (EU) 2022/1925

- **Full Title:** Regulation (EU) 2022/1925 of the European Parliament and of the Council of 14 September 2022 on contestable and fair markets in the digital sector and amending Directives (EU) 2019/1937 and (EU) 2020/1828 (Digital Markets Act)
- **Common Abbreviation:** DMA
- **Legal Instrument:** Regulation (directly applicable)
- **CELEX Number:** `32022R1925`
- **ELI Identifier:** `http://data.europa.eu/eli/reg/2022/1925/oj`
- **Official EUR-Lex URL:** `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R1925`
- **Publication Date:** 12 October 2022
- **Entry into Force:** 1 November 2022
- **General Application Date:** 2 May 2023 (6 months after entry into force)
- **Gatekeeper Compliance Deadline:** 7 March 2024 (6 months after designation of core platform services).
- **Transposition Deadline:** `null` (Regulation)
- **Corrigenda:** None.
- **Consolidated Version:** None yet published.
- **Available Formats on EUR-Lex:** HTML, XML, PDF.

---

### 3.5 Data Act — Regulation (EU) 2023/2854

- **Full Title:** Regulation (EU) 2023/2854 of the European Parliament and of the Council of 13 December 2023 on harmonised rules on fair access to and use of data and amending Regulation (EU) 2017/2394 and Directive (EU) 2020/1828 (Data Act)
- **Common Abbreviation:** Data Act
- **Legal Instrument:** Regulation (directly applicable)
- **CELEX Number:** `32023R2854`
- **ELI Identifier:** `http://data.europa.eu/eli/reg/2023/2854/oj`
- **Official EUR-Lex URL:** `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R2854`
- **Publication Date:** 22 December 2023
- **Entry into Force:** 11 January 2024
- **General Application Date:** 12 September 2025 (Article 50(1))
- **Staggered Milestones:** Design obligations for connected products (Article 3(1)) apply to products placed on the market after 12 September 2026 (Article 50(2)).
- **Transposition Deadline:** `null` (Regulation)
- **Corrigenda:** None.
- **Consolidated Version:** None yet published.
- **Available Formats on EUR-Lex:** HTML, XML, PDF.

---

### 3.6 NIS2 Directive — Directive (EU) 2022/2555

- **Full Title:** Directive (EU) 2022/2555 of the European Parliament and of the Council of 14 December 2022 on measures for a high common level of cybersecurity across the Union, amending Regulation (EU) No 910/2014 and Directive (EU) 2018/1972, and repealing Directive (EU) 2016/1148 (NIS 2 Directive)
- **Common Abbreviation:** NIS2
- **Legal Instrument:** Directive (requires national transposition)
- **CELEX Number:** `32022L2555`
  - `3`: Sector 3
  - `2022`: Year of adoption
  - `L`: Directive (*Loi/Lex*)
  - `2555`: Document number
- **ELI Identifier:** `http://data.europa.eu/eli/dir/2022/2555/oj`
- **Official EUR-Lex URL:** `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2555`
- **Publication Date:** 27 December 2022
- **Entry into Force:** 16 January 2023
- **Transposition Deadline:** 17 October 2024 (Member States were required to adopt national measures by this date)
- **Application Date:** 18 October 2024 (national implementing measures become enforceable)
- **Corrigenda:** None.
- **Consolidated Version:** None yet published.
- **Available Formats on EUR-Lex:** HTML, XML, PDF.

---

## 4. CELEX and ELI Structure Guide

### CELEX Dissection and Classification
EUR-Lex CELEX identifiers follow a deterministic schema:
`[Sector][Year][DocType][Number][Suffix]`

1. **Original Legal Acts (Authentic)**:
   - Format: `3YYYY[DocType]NNNN` (or Sectors 1–4)
   - Examples: `32024R1689` (AI Act), `32016R0679` (GDPR), `32022L2555` (NIS2)
   - Sector `3`: Secondary EU legislation (Regulations, Directives, Decisions).
   - DocType: `R` (Regulation), `L` (Directive), `D` (Decision).
   - Number: 4 digits with leading zeros (e.g., `0679` for GDPR).

2. **Consolidated Texts (Editorial synthesis)**:
   - Format: `0YYYY[DocType]NNNN-YYYYMMDD`
   - Example: `02016R0679-20210304` (GDPR consolidated as of 4 March 2021).
   - Sector `0`: Consolidated family. Suffix represents the effective consolidation cutoff date.

3. **Corrigenda (Official corrections in OJ)**:
   - Format: `3YYYY[DocType]NNNNR(XX)`
   - Examples: `32024R1689R(01)` (AI Act Corrigendum 1), `32016R0679R(02)` (GDPR Corrigendum 2).
   - Suffix: `R(` followed by a 2-digit sequential number and `)`. Rectifies linguistic/typographical errors in the authentic OJ publication.

### European Legislation Identifier (ELI)
ELI provides a permanent, language-neutral, URI-based standard:
- Base: `http://data.europa.eu/eli/`
- Type: `reg` (Regulation) or `dir` (Directive)
- Year and Number: `2024/1689`
- Version: `/oj` (Official Journal authentic text) or `/{date}` (Consolidated version as of date).

