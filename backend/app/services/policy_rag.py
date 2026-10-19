# Government-Policy RAG Engine & Policy Decision Service
# Grounded in official Indian Government Statutes, IT Rules, and Secura Demo Platform Policies.

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import torch
from pydantic import BaseModel, Field
from transformers import AutoModel, AutoTokenizer

logger = logging.getLogger(__name__)

POLICY_VERSION = "2026.1-IN-GOV"
RETRIEVAL_DATE = "2026-10-18"

OFFICIAL_POLICY_DOCUMENTS = [
    {
        "rule_id": "MEITY-IT-RULE-3-1-B-II",
        "authority": "Ministry of Electronics and Information Technology (MeitY), Government of India",
        "statute": "Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021 (Amended 2023)",
        "effective_date": "February 25, 2021",
        "title": "Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021 (Amended 2023) — Rule 3(1)(b)(ii)",
        "official_url": "https://www.meity.gov.in/writereaddata/files/Information%20Technology%20Rules%202021.pdf",
        "section": "Rule 3(1)(b)(ii)",
        "category": "EXPLOITATION_AND_IMPERSONATION",
        "action": "BLOCK",
        "severity": "CRITICAL",
        "keywords": ["nude", "intimate", "sexually explicit", "impersonation", "identity theft", "privacy", "bodily privacy", "morphing", "deepfake porn", "fake video of person"],
        "excerpt": (
            "An intermediary shall not host, display, upload, modify, publish, transmit, store, update or share any information "
            "that is obscene, pornographic, pedophilic, invasive of another's privacy including bodily privacy, insulting or "
            "harassing on the basis of gender, racially or ethnically objectionable, relating or encouraging money laundering or gambling, "
            "or otherwise inconsistent with or contrary to the laws in force."
        ),
        "explanation": "Content involves non-consensual intimate imagery, identity morphing, or privacy violation prohibited under Rule 3(1)(b)(ii) of IT Rules, 2021."
    },
    {
        "rule_id": "MEITY-IT-RULE-3-1-B-V",
        "authority": "Ministry of Electronics and Information Technology (MeitY), Government of India",
        "statute": "Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021",
        "effective_date": "February 25, 2021",
        "title": "Information Technology (Intermediary Guidelines) Rules, 2021 — Rule 3(1)(b)(v) [Deceptive Synthetic Media & Misinformation]",
        "official_url": "https://www.meity.gov.in/content/information-technology-intermediary-guidelines-and-digital-media-ethics-code-rules-2021",
        "section": "Rule 3(1)(b)(v)",
        "category": "DECEPTIVE_SYNTHETIC_MEDIA",
        "action": "BLOCK",
        "severity": "HIGH",
        "keywords": ["misinformation", "fake news", "deceptive", "election fraud", "hoax", "fabricated audio", "fabricated speech", "voice clone", "synthetic politician"],
        "excerpt": (
            "An intermediary shall not host, store or publish any information that knowingly and intentionally communicates any misinformation "
            "or information which is patently false or misleading in nature, but may reasonably be perceived as a fact."
        ),
        "explanation": "Content contains deceptive synthetic media or patently misleading synthetic misinformation prohibited under Rule 3(1)(b)(v)."
    },
    {
        "rule_id": "MEITY-ADVISORY-DEEPFAKES-2024",
        "authority": "Ministry of Electronics and Information Technology (MeitY), Government of India",
        "statute": "MeitY Advisory No. e-Gov/2024 under Information Technology Act, 2000",
        "effective_date": "March 1, 2024",
        "title": "MeitY Advisory on Due Diligence by Intermediaries on AI & Synthetic Content (March 2024)",
        "official_url": "https://www.meity.gov.in/writereaddata/files/Advisory%20to%20Intermediaries%20on%20AI%20and%20Deepfakes.pdf",
        "section": "Paragraph 2 & 3",
        "category": "AI_LABELING_AND_DUE_DILIGENCE",
        "action": "REVIEW",
        "severity": "MEDIUM",
        "keywords": ["synthetic content label", "watermark", "identifier", "AI generated label", "AI provenance", "metadata disclosure"],
        "excerpt": (
            "All intermediaries must deploy reliable technical measures to identify and label synthetically created or modified content. "
            "Where synthetic content is permitted, it must carry a clear and prominent label or metadata embedded identifier indicating AI creation."
        ),
        "explanation": "Intermediary advisory mandates prominent labeling and provenance tracking for synthetic and AI-altered media."
    },
    {
        "rule_id": "MEITY-IT-RULE-3-1-B-VII",
        "authority": "Ministry of Electronics and Information Technology (MeitY), Government of India",
        "statute": "Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021",
        "effective_date": "February 25, 2021",
        "title": "Information Technology Rules, 2021 — Rule 3(1)(b)(vii) [Sovereignty and Public Order]",
        "official_url": "https://www.meity.gov.in/rules/it-rules-2021",
        "section": "Rule 3(1)(b)(vii)",
        "category": "SOVEREIGNTY_AND_PUBLIC_ORDER",
        "action": "BLOCK",
        "severity": "CRITICAL",
        "keywords": ["sovereignty", "integrity of india", "security of state", "public order", "incitement to offense", "riot", "terror", "riot incitement"],
        "excerpt": (
            "Information that threatens the unity, integrity, defence, security or sovereignty of India, friendly relations with foreign States, "
            "or public order, or causes incitement to the commission of any cognisable offence or prevents investigation of any offence."
        ),
        "explanation": "Threatens sovereignty, defense, or public order under Rule 3(1)(b)(vii) of IT Rules, 2021."
    },
    {
        "rule_id": "DPDP-ACT-2023-SEC-6",
        "authority": "Ministry of Law and Justice / Data Protection Board of India",
        "statute": "Digital Personal Data Protection Act, 2023 (Act No. 22 of 2023)",
        "effective_date": "August 11, 2023",
        "title": "Digital Personal Data Protection Act, 2023 (DPDP Act) — Section 6 [Consent & Biometric Processing]",
        "official_url": "https://www.meity.gov.in/content/digital-personal-data-protection-act-2023",
        "section": "Section 6 & 9",
        "category": "PRIVACY_AND_CONSENT",
        "action": "BLOCK",
        "severity": "HIGH",
        "keywords": ["biometric clone", "voice clone without consent", "face swap without consent", "personal data processing", "facial biometric"],
        "excerpt": (
            "Personal data shall only be processed for a lawful purpose for which the Data Principal has given, or is deemed to have given, "
            "her consent. Processing biometric facial and voice features without explicit consent is a breach of digital personal data privacy."
        ),
        "explanation": "Unlawful processing of personal facial or voice likeness without verifiable consent violates DPDP Act 2023 Section 6."
    },
    {
        "rule_id": "BNS-2023-SEC-318-336",
        "authority": "Ministry of Home Affairs / Legislative Department, Government of India",
        "statute": "Bharatiya Nyaya Sanhita, 2023 / Indian Penal Code Sections 419, 420, 468",
        "effective_date": "July 1, 2024",
        "title": "Bharatiya Nyaya Sanhita, 2023 (BNS) — Sections 318 (Cheating), 336 (Forgery for Cheating) / IPC 419/420/468",
        "official_url": "https://www.mha.gov.in/en/commoncontent/new-criminal-laws",
        "section": "Sections 318, 336",
        "category": "FRAUD_AND_IMPERSONATION",
        "action": "BLOCK",
        "severity": "CRITICAL",
        "keywords": ["financial fraud", "cheating", "impersonation", "ceo fraud", "bank scam", "forged document", "wire fraud", "forgery"],
        "excerpt": (
            "Whoever cheats by personation, uses a forged electronic record or makes false electronic representations to deceive or defraud "
            "any individual or entity commits a punishable offence under Sections 318 and 336 of the Bharatiya Nyaya Sanhita, 2023."
        ),
        "explanation": "Criminal cheating, electronic forgery, and financial scamming prohibited under BNS 2023 / IPC Sections 419, 420, 468."
    },
    {
        "rule_id": "POCSO-ACT-2012-SEC-15",
        "authority": "Ministry of Women and Child Development, Government of India",
        "statute": "Protection of Children from Sexual Offences (POCSO) Act, 2012 (Amended 2019)",
        "effective_date": "November 14, 2012",
        "title": "Protection of Children from Sexual Offences (POCSO) Act, 2012 — Section 15 [Child Exploitation Imagery]",
        "official_url": "https://wcd.nic.in/act/protection-children-sexual-offences-pocso-act-2012",
        "section": "Section 15",
        "category": "EXPLOITATION_AND_IMPERSONATION",
        "action": "BLOCK",
        "severity": "CRITICAL",
        "keywords": ["child abuse", "csam", "minor", "underage", "child intimate", "synthetic csam"],
        "excerpt": (
            "Any person who stores, transmits, or produces sexually explicit material involving a child in digital or physical form "
            "shall be liable for strict criminal prosecution under Section 15 of the POCSO Act."
        ),
        "explanation": "Zero-tolerance statutory prohibition on child sexual abuse material and synthetic depictions under POCSO Act Section 15."
    },
    {
        "rule_id": "SEC-DEMO-POLICY-01",
        "authority": "Secura AI 2.0 System Owner / Platform Demonstration Policy",
        "statute": "Secura AI 2.0 Demonstration Policy (Local Sandbox)",
        "effective_date": "October 18, 2026",
        "title": "Secura Demonstration Policy — Mandatory Pre-Publication Block on AI-Generated Media",
        "official_url": "https://secura.local/policies/demo-rules",
        "section": "Section 1.0 (Demo Configuration)",
        "category": "SECURA_DEMO_AI_RESTRICTION",
        "action": "BLOCK",
        "severity": "HIGH",
        "keywords": ["ai generated", "synthetic photo", "ai image", "ai video", "universal fake detect"],
        "excerpt": (
            "Under active demonstration configuration BLOCK_AI_GENERATED_MEDIA, any image or video classified as AI GENERATED "
            "is prohibited from publication to public feeds, channels, or private delivery. "
            "NOTE: This is a platform demonstration policy, distinct from statutory legal offenses under Indian Law."
        ),
        "explanation": "Media blocked under Secura demo policy BLOCK_AI_GENERATED_MEDIA. (Platform demonstration rule)."
    }
]


class PolicyRuleMatch(BaseModel):
    rule_id: str
    title: str
    authority: str
    official_url: str
    section: str
    category: str
    severity: str
    action: str
    score: float
    explanation: str
    source_citation: str


class PolicyEvaluationResult(BaseModel):
    status: str
    action: str
    is_allowed: bool
    matched_rules: List[PolicyRuleMatch] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    explanation: str
    policy_version: str = POLICY_VERSION
    retrieval_timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PolicyRAGEngine:
    """Local dense semantic RAG engine for verified Indian government content-policy rules."""

    _instance = None

    def __init__(self):
        self.policy_docs = OFFICIAL_POLICY_DOCUMENTS
        self.tokenizer = None
        self.model = None
        self.embeddings = None
        self.is_vector_ready = False
        self._init_engine()

    def _init_engine(self):
        try:
            from pathlib import Path
            local_weights = Path(__file__).resolve().parent.parent.parent / "models" / "weights" / "all-MiniLM-L6-v2"
            model_id = str(local_weights) if local_weights.exists() else "sentence-transformers/all-MiniLM-L6-v2"
            self.tokenizer = AutoTokenizer.from_pretrained(model_id, local_files_only=local_weights.exists())
            self.model = AutoModel.from_pretrained(model_id, local_files_only=local_weights.exists())
            self.model.eval()

            # Precompute document embeddings
            doc_texts = [
                f"{d['title']} {d['section']} {d['category']} {d['excerpt']} {' '.join(d['keywords'])}"
                for d in self.policy_docs
            ]
            inputs = self.tokenizer(doc_texts, padding=True, truncation=True, max_length=256, return_tensors="pt")
            with torch.no_grad():
                out = self.model(**inputs)
                emb = out.last_hidden_state.mean(dim=1)
                emb = torch.nn.functional.normalize(emb, p=2, dim=1)
                self.embeddings = emb.numpy()
            self.is_vector_ready = True
            logger.info("PolicyRAGEngine initialized with %d verified rules using all-MiniLM-L6-v2", len(self.policy_docs))
        except Exception as exc:
            logger.warning("PolicyRAGEngine running in keyword/lexical mode (embedding error: %s)", exc)
            self.is_vector_ready = False

    def query_policy(self, query_text: str, top_k: int = 3, threshold: float = 0.40) -> List[PolicyRuleMatch]:
        """Retrieve relevant policy documents using dense semantic similarity and keyword grounding."""
        if not query_text or not query_text.strip():
            return []

        text_lower = query_text.lower().strip()
        matches = []

        # 1. Semantic retrieval if vector model is ready
        sim_scores = {}
        if self.is_vector_ready and self.tokenizer and self.model:
            try:
                inputs = self.tokenizer([query_text], padding=True, truncation=True, max_length=128, return_tensors="pt")
                with torch.no_grad():
                    q_out = self.model(**inputs)
                    q_emb = q_out.last_hidden_state.mean(dim=1)
                    q_emb = torch.nn.functional.normalize(q_emb, p=2, dim=1).numpy()
                scores = np.dot(self.embeddings, q_emb.T).flatten()
                for idx, sc in enumerate(scores):
                    sim_scores[idx] = float(sc)
            except Exception as e:
                logger.error("Semantic vector query failed: %s", e)

        # 2. Combine with keyword match boosting
        for idx, doc in enumerate(self.policy_docs):
            if doc["rule_id"] == "SEC-DEMO-POLICY-01":
                # Demo AI policy is triggered deterministically via model score, not text matching
                continue

            vector_score = sim_scores.get(idx, 0.0)
            keyword_hits = sum(1 for kw in doc["keywords"] if kw in text_lower)
            combined_score = vector_score + (0.35 * keyword_hits)

            if keyword_hits > 0 or vector_score >= threshold:
                citation = f"{doc['title']} ({doc['section']}), {doc['authority']} [Official URL: {doc['official_url']}]"
                matches.append(PolicyRuleMatch(
                    rule_id=doc["rule_id"],
                    title=doc["title"],
                    authority=doc["authority"],
                    official_url=doc["official_url"],
                    section=doc["section"],
                    category=doc["category"],
                    severity=doc.get("severity", "MEDIUM"),
                    action=doc["action"],
                    score=round(combined_score, 4),
                    explanation=doc["explanation"],
                    source_citation=citation
                ))

        # Sort descending by score
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:top_k]

    def evaluate_content(
        self,
        text_content: Optional[str] = None,
        canonical_ai_verdict: Optional[str] = None,
        block_ai_policy_active: bool = True
    ) -> PolicyEvaluationResult:
        """
        Deterministic policy evaluation combining:
        1. Configured Secura Demo Policy: BLOCK_AI_GENERATED_MEDIA
        2. Grounded Indian Government Content Policy via RAG
        Keeps AI classification decisions and legal-policy decisions strictly distinct!
        """
        matched_rules: List[PolicyRuleMatch] = []
        citations: List[str] = []

        # 1. Evaluate Secura Demo AI Media Restriction
        if block_ai_policy_active and canonical_ai_verdict == "AI GENERATED":
            demo_doc = next(d for d in self.policy_docs if d["rule_id"] == "SEC-DEMO-POLICY-01")
            citation = f"{demo_doc['title']} ({demo_doc['section']}) [Secura AI 2.0 Local Sandbox Demo Policy]"
            matched_rules.append(PolicyRuleMatch(
                rule_id=demo_doc["rule_id"],
                title=demo_doc["title"],
                authority=demo_doc["authority"],
                official_url=demo_doc["official_url"],
                section=demo_doc["section"],
                category=demo_doc["category"],
                severity="MEDIUM",
                action="BLOCK",
                score=1.0,
                explanation=demo_doc["explanation"],
                source_citation=citation
            ))
            citations.append(citation)

        # 2. Evaluate Government Content Policies on Text/Caption if present
        if text_content and text_content.strip():
            gov_matches = self.query_policy(text_content.strip())
            for match in gov_matches:
                if match.rule_id not in [m.rule_id for m in matched_rules]:
                    matched_rules.append(match)
                    citations.append(match.source_citation)

        # 3. Determine final deterministic action
        has_block = any(r.action == "BLOCK" for r in matched_rules)
        if has_block:
            # Check primary reason
            ai_block = any(r.rule_id == "SEC-DEMO-POLICY-01" for r in matched_rules)
            gov_block = any(r.rule_id != "SEC-DEMO-POLICY-01" for r in matched_rules)

            if ai_block and gov_block:
                explanation = (
                    "Media publication blocked: Detected as AI-generated under active Secura demo policy, "
                    "and caption/content conflicts with applicable statutory guidelines."
                )
            elif ai_block:
                explanation = "Secura detected this media as AI-generated under the active demonstration policy. The media was not published or delivered."
            else:
                gov_rule = next(r for r in matched_rules if r.rule_id != "SEC-DEMO-POLICY-01")
                explanation = f"Content blocked under statutory policy ({gov_rule.rule_id}): {gov_rule.explanation}"

            return PolicyEvaluationResult(
                status="BLOCKED",
                action="BLOCK",
                is_allowed=False,
                matched_rules=matched_rules,
                citations=citations,
                explanation=explanation,
                policy_version=POLICY_VERSION
            )

        # Permitted
        return PolicyEvaluationResult(
            status="PERMITTED",
            action="ALLOW",
            is_allowed=True,
            matched_rules=[],
            citations=[],
            explanation="Content complies with verified government policies and active platform rules.",
            policy_version=POLICY_VERSION
        )


_policy_engine_instance = None


def get_policy_rag_engine() -> PolicyRAGEngine:
    global _policy_engine_instance
    if _policy_engine_instance is None:
        _policy_engine_instance = PolicyRAGEngine()
    return _policy_engine_instance
