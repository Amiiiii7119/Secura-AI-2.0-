# Government Policy RAG: Legal & Statutory Knowledge Base

## 1. Statutory Foundations
The RAG system indexes 8 official statutory documents from the Gazette of India and MeitY:

| ID | Statute / Framework | Governing Authority | Key Mandate |
|---|---|---|---|
| `IT_RULES_2021_3_1_B` | IT (Intermediary Guidelines) Rules 2021 | MeitY | Due diligence to prevent hosting impersonation, IP infringement, and CSAM |
| `IT_RULES_2023_AMENDMENT` | IT Amendment Rules 2023 | MeitY | Mandatory labeling of synthetically altered or AI-generated media |
| `MEITY_ADVISORY_MARCH_2024` | MeitY Deepfake Advisory 2024 | MeitY | Platforms must implement automated tools to identify and label deepfakes |
| `DPDP_ACT_2023` | Digital Personal Data Protection Act 2023 | Govt of India | Prohibition of biometric voice/face cloning without explicit consent |
| `BNS_2023_419_420` | Bharatiya Nyaya Sanhita 2023 (Sec 318/319) | Ministry of Home Affairs | Criminal penalties for digital impersonation and cheating by personation |
| `IPC_SECTION_468` | Indian Penal Code (IPC 468) | Govt of India | Forgery for the purpose of cheating using synthetic documents or signatures |
| `POCSO_ACT_2012` | Protection of Children from Sexual Offences | Ministry of WCD | Zero tolerance / mandatory statutory block for CSAM / synthetic minor abuse |
| `ELECTION_COMMISSION_DEEPFAKE_2024` | ECI Model Code of Conduct Advisory | Election Commission of India | Prohibition of synthetic disinformation during democratic electoral processes |

## 2. Vector Retrieval Engine
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional cosine space).
- **Retrieval Threshold:** Minimum cosine similarity `0.35` for statutory relevance matching.
- **Strict Policy Separation:** The demo policy (`BLOCK_AI_GENERATED_MEDIA`) operates as a demonstration flag, distinct from statutory violations which trigger unconditional platform-level blocking.