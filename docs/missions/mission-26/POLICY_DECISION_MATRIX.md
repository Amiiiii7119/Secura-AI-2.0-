# Policy Decision Matrix & Enforcement Logic

## 1. Decision Hierarchy

```
                  +--------------------------------+
                  | Content / Media Under Review   |
                  +--------------------------------+
                                  |
                                  v
                  +--------------------------------+
                  |  Statutory RAG Analysis Pass   |
                  +--------------------------------+
                                  |
            +---------------------+---------------------+
            | (Statutory Violation Found?)              |
           YES                                          NO
            |                                           |
            v                                           v
+------------------------+             +--------------------------------+
| ACTION: BLOCK          |             | AI Fake Detection Inference    |
| Status: 403 Forbidden  |             +--------------------------------+
| Statutory Citations    |                              |
+------------------------+             +----------------+---------------+
                                       |                                |
                             (Score >= 0.50 Synthetic)     (Score < 0.50 Authentic)
                                       |                                |
                        +--------------+--------------+                 v
                        | Demo Policy Active?         |       +--------------------+
                       YES                            NO      | ACTION: ALLOW      |
                        |                             |       | Verdict: Authentic |
                        v                             v       +--------------------+
             +--------------------+       +---------------------+
             | ACTION: BLOCK      |       | ACTION: LABEL       |
             | Pre-Publication    |       | Verdict: Synthetic  |
             | 403 Interception   |       | Banner: "AI-Gen"    |
             +--------------------+       +---------------------+
```

## 2. Moderation Verdicts Summary
- **ALLOW:** Authentic media (< 0.50 score) with no policy or statutory violations.
- **LABEL:** Synthetic media (>= 0.50 score) when demo blocking is disabled; content is marked with transparent AI provenance tags.
- **BLOCK:** Content violating statutory provisions or synthetic media when demo policy enforcement is active.