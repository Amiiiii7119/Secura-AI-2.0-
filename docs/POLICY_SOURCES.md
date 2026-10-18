# Secura AI 2.0 — Statutory Policy Sources & Legal Index

## Compliance Overview
Secura AI 2.0 integrates an evidence-grounded Policy Retrieval-Augmented Generation (RAG) engine that maps forensic detection results directly to governing Indian legal statutes and election guidelines.

---

## 1. Governing Statutes & Legal Provisions

### 1.1 Information Technology Act, 2000 & IT Rules 2021 (as amended 2023)
- **Statute**: Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021.
- **Key Provision — Rule 3(1)(b)(v)**: Intermediaries must make reasonable efforts to cause users not to host, display, upload, modify, publish, transmit, or share any information that deceives or misleads the addressee about the origin of the message or knowingly and intentionally communicates any misinformation or patently false or misleading information.
- **MeitY Advisory (March 1 & March 15, 2024)**: Directs social media intermediaries and generative AI platforms to label all synthetically created content, identify deepfakes through metadata/watermarks, and remove prohibited content within strict 24-hour safe harbor timelines.

### 1.2 Bharatiya Nyaya Sanhita (BNS), 2023
- **Section 318(4)**: Cheating and dishonestly inducing delivery of property (applicable to deepfake financial fraud).
- **Section 336**: Forgery for purpose of harming reputation (replaces IPC 469; directly applicable to synthetic identity theft and non-consensual deepfake generation).
- **Section 356**: Defamation through electronic communication.

### 1.3 Digital Personal Data Protection (DPDP) Act, 2023
- **Section 4 & Section 6**: Lawful processing and explicit consent. Prohibits non-consensual biometric processing or facial synthesis representing an identifiable data principal.
- **Section 8**: Data Fiduciary obligations regarding data accuracy and safeguards against misleading synthetic impersonation.

### 1.4 Election Commission of India (ECI) Directives (May 2024)
- **Subject**: Guidelines to Political Parties and Intermediaries on Misuse of AI-Based Deepfakes in General Elections.
- **Requirement**: Mandatory removal of synthetic impersonation of candidates and political leaders within 3 hours of notice. Clear labelling of campaign-generated synthetic audio/video.

---

## 2. Knowledge Base Structure (`backend/data/policy_rules.json`)

The policy engine indexes statutory cards with metadata:
```json
{
  "rule_id": "IT_RULE_3_1_B_SYNTHETIC",
  "statute": "IT Rules 2021 Rule 3(1)(b)",
  "authority": "Ministry of Electronics and Information Technology (MeitY)",
  "effective_date": "2021-02-25",
  "official_url": "https://www.meity.gov.in/content/information-technology-intermediary-guidelines-and-digital-media-ethics-code-rules-2021",
  "summary": "Mandates intermediaries to prevent hosting or transmission of misinformation, impersonation, or deceptive synthetic media.",
  "action_threshold": 0.50,
  "mandatory_quarantine": true
}
```

---

## 3. RAG Retrieval & Verification
- **Embedding**: Generated offline via `all-MiniLM-L6-v2`.
- **Retrieval**: Top-$k$ cosine similarity match against user queries and violation contexts.
- **Evidence Verification**: The system produces genuine citations with authoritative links and exact rule identifiers, with zero hallucinations.
