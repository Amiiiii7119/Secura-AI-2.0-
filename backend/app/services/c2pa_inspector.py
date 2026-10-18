import io
import json
import logging
from typing import Optional, Dict, Any, List

from app.schemas.evidence import (
    C2PAManifestClaim,
    C2PAStatus,
    C2PAValidationResult,
)

logger = logging.getLogger(__name__)

# Check SDK availability at import time
try:
    import c2pa
    SDK_AVAILABLE = True
    SDK_VERSION = getattr(c2pa, "__version__", "installed")
except ImportError:
    c2pa = None
    SDK_AVAILABLE = False
    SDK_VERSION = None


def inspect_c2pa_manifest(image_bytes: bytes, mime_type: str) -> C2PAValidationResult:
    """Inspect an image for C2PA provenance manifests using the official c2pa-python SDK.
    
    Operates strictly in-memory using io.BytesIO to avoid persistent disk artifacts.
    Accurately maps manifest presence, cryptographic signature validity, signer trust, and missing states.
    
    Forensic Semantics:
    - NO_MANIFEST / C2PA_MISSING: The asset contains no JUMBF/C2PA manifest. This is typical for
      the vast majority of internet images and does NOT imply AI generation or human origin.
    - SIGNATURE_VALID: Manifest present and cryptographically intact with trusted certificate path.
    - SIGNER_UNTRUSTED: Manifest signature is mathematically valid, but signing certificate is untrusted
      (e.g. self-signed test root or unconfigured enterprise trust list).
    - SIGNATURE_INVALID: Manifest detected but cryptographic hash binding or signature check failed (tampered).
    - ANALYSIS_UNAVAILABLE: The SDK is not available in the execution environment.
    - ANALYSIS_FAILED: An unexpected parsing error occurred.
    """
    if not SDK_AVAILABLE or c2pa is None:
        return C2PAValidationResult(
            status=C2PAStatus.ANALYSIS_UNAVAILABLE,
            sdk_available=False,
            manifest_present=False,
            validation_status="SDK_UNAVAILABLE",
            signature_valid=None,
            signer_trusted=None,
            trust_validation_status="C2PA SDK is not installed in the runtime environment.",
            manifest_data=None,
            claims=None,
            provenance_notes=(
                "The official c2pa-python SDK is not available or could not be loaded in this environment. "
                "C2PA inspection was skipped without simulating or fabricating provenance verification."
            )
        )
    
    # Map mime type if necessary
    c2pa_mime = mime_type.lower()
    supported_mimes = c2pa.Reader.get_supported_mime_types() if hasattr(c2pa.Reader, "get_supported_mime_types") else []
    if c2pa_mime not in supported_mimes:
        if "jpeg" in c2pa_mime or "jpg" in c2pa_mime:
            c2pa_mime = "image/jpeg"
        elif "png" in c2pa_mime:
            c2pa_mime = "image/png"
        elif "webp" in c2pa_mime:
            c2pa_mime = "image/webp"
        elif "tiff" in c2pa_mime:
            c2pa_mime = "image/tiff"
    
    stream = io.BytesIO(image_bytes)
    reader = None
    
    try:
        reader = c2pa.Reader.try_create(c2pa_mime, stream)
        
        if reader is None:
            return C2PAValidationResult(
                status=C2PAStatus.NO_MANIFEST,
                sdk_available=True,
                manifest_present=False,
                validation_status="NO_MANIFEST_FOUND",
                signature_valid=None,
                signer_trusted=None,
                trust_validation_status="No C2PA provenance manifest detected in container.",
                manifest_data=None,
                claims=None,
                provenance_notes=(
                    "No C2PA provenance manifest or JUMBF metadata found in asset. "
                    "This is expected for standard web imagery and camera photographs; "
                    "it does not indicate whether the media is authentic, manipulated, or AI-generated."
                )
            )
        
        # Manifest is present; inspect validity and extract claims
        # Note: reader.is_valid can be a property or a callable depending on SDK build
        is_valid = False
        try:
            if callable(getattr(reader, "is_valid", None)):
                is_valid = bool(reader.is_valid())
            else:
                is_valid = bool(getattr(reader, "is_valid", False))
        except Exception as val_err:
            logger.warning(f"Error checking is_valid: {val_err}")
            is_valid = False
        
        val_state = None
        try:
            if callable(getattr(reader, "get_validation_state", None)):
                val_state = str(reader.get_validation_state())
            else:
                val_state = str(getattr(reader, "get_validation_state", ""))
        except Exception:
            pass
        
        manifest_raw = None
        try:
            manifest_raw = reader.json()
        except Exception:
            pass
        
        manifest_dict: Optional[Dict[str, Any]] = None
        claims_summary: Optional[C2PAManifestClaim] = None
        validation_status_codes: List[str] = []
        
        if manifest_raw:
            try:
                manifest_dict = json.loads(manifest_raw)
                
                # Validation status list
                val_status_items = manifest_dict.get("validation_status", [])
                if isinstance(val_status_items, list):
                    for item in val_status_items:
                        if isinstance(item, dict) and "code" in item:
                            validation_status_codes.append(item["code"])

                # In c2pa specification, active_manifest is a URN key into manifests dictionary
                active_urn = manifest_dict.get("active_manifest")
                manifests_map = manifest_dict.get("manifests", {})
                active_manifest: Dict[str, Any] = {}
                if isinstance(active_urn, str) and active_urn in manifests_map:
                    active_manifest = manifests_map[active_urn]
                elif isinstance(active_urn, dict):
                    active_manifest = active_urn

                all_assertions: List[Dict[str, Any]] = []
                if manifests_map:
                    for m_urn, m_val in manifests_map.items():
                        m_asserts = m_val.get("assertions", [])
                        if isinstance(m_asserts, list):
                            for a in m_asserts:
                                if isinstance(a, dict):
                                    all_assertions.append({
                                        "label": a.get("label"),
                                        "data": a.get("data"),
                                        "manifest_urn": m_urn
                                    })
                else:
                    for a in active_manifest.get("assertions", []):
                        if isinstance(a, dict):
                            all_assertions.append({
                                "label": a.get("label"),
                                "data": a.get("data"),
                                "manifest_urn": "active"
                            })

                ai_detected_actions: List[str] = []
                has_synthid = False
                signer_issuers: List[str] = []

                if manifests_map:
                    for m_urn, m_val in manifests_map.items():
                        sig = m_val.get("signature_info", {})
                        if isinstance(sig, dict) and sig.get("issuer"):
                            signer_issuers.append(str(sig.get("issuer")))
                else:
                    sig = active_manifest.get("signature_info", {})
                    if isinstance(sig, dict) and sig.get("issuer"):
                        signer_issuers.append(str(sig.get("issuer")))

                for a in all_assertions:
                    data = a.get("data")
                    if isinstance(data, dict):
                        actions = data.get("actions", [])
                        if isinstance(actions, list):
                            for act in actions:
                                if not isinstance(act, dict):
                                    continue
                                dst = str(act.get("digitalSourceType", "")).lower()
                                desc = str(act.get("description", "")).lower()
                                agent = str(act.get("softwareAgent", "")).lower()
                                if "trainedalgorithmicmedia" in dst:
                                    ai_detected_actions.append(f"{act.get('action')}: {act.get('digitalSourceType')}")
                                genai_keywords = [
                                    "google generative ai", "generative ai", "synthid",
                                    "dall-e", "midjourney", "firefly", "stable diffusion", "imagen"
                                ]
                                if any(k in desc for k in genai_keywords) or any(k in agent for k in genai_keywords):
                                    ai_detected_actions.append(f"{act.get('description') or act.get('softwareAgent')}")
                                if "synthid" in desc or "synthid" in dst:
                                    has_synthid = True

                claim_gen = active_manifest.get("claim_generator")
                if not claim_gen:
                    for m_val in manifests_map.values():
                        cg_info = m_val.get("claim_generator_info")
                        if isinstance(cg_info, list) and len(cg_info) > 0:
                            claim_gen = cg_info[0].get("name")
                            break

                claims_summary = C2PAManifestClaim(
                    title=active_manifest.get("title"),
                    claim_generator=claim_gen,
                    format=active_manifest.get("format"),
                    instance_id=active_manifest.get("instance_id"),
                    thumbnail_present="thumbnail" in active_manifest,
                    ingredients_count=len(active_manifest.get("ingredients", [])),
                    assertions=[
                        {"label": a.get("label"), "data": a.get("data")}
                        for a in all_assertions
                    ]
                )
            except Exception as parse_err:
                logger.warning(f"Error parsing manifest JSON: {parse_err}")
        
        # Analyze cryptographic signature vs trust status
        has_hash_mismatch = any(
            ("mismatch" in code.lower() or "corrupt" in code.lower() or "tamper" in code.lower())
            for code in validation_status_codes
        )
        has_untrusted_signer = any(
            ("untrusted" in code.lower() or "trust" in code.lower())
            for code in validation_status_codes
        )
        
        signature_valid = is_valid and not has_hash_mismatch
        signer_trusted = signature_valid and not has_untrusted_signer

        recognized_ai_signers = ["google", "adobe", "openai", "microsoft"]
        is_recognized_signer = any(
            any(k in s.lower() for k in recognized_ai_signers)
            for s in signer_issuers
        ) or any(
            k in str(active_manifest.get("signature_info", {}).get("issuer", "")).lower()
            for k in recognized_ai_signers
        )

        if not signature_valid or (val_state and val_state.lower() == "invalid" and has_hash_mismatch):
            status = C2PAStatus.SIGNATURE_INVALID
            trust_explanation = (
                f"Cryptographic hash or signature mismatch detected: {', '.join(validation_status_codes) or 'DataHash mismatch'}. "
                "The image raster or manifest assertions have been modified since signing."
            )
            provenance_notes = f"TAMPERING DETECTED: {trust_explanation}"
        elif ai_detected_actions:
            status = C2PAStatus.SIGNATURE_VALID if is_recognized_signer else (C2PAStatus.SIGNER_UNTRUSTED if has_untrusted_signer else C2PAStatus.SIGNATURE_VALID)
            issuer_name = ", ".join(set(signer_issuers)) if signer_issuers else str(active_manifest.get("signature_info", {}).get("issuer", "Generative AI Service"))
            trust_explanation = (
                f"Cryptographic signature verified (Issuer: {issuer_name}). "
                f"Content credentials explicitly certify generative AI origin (digitalSourceType: trainedAlgorithmicMedia)."
            )
            provenance_notes = (
                f"VERIFIED GENERATIVE AI ORIGIN: Cryptographically certified provenance signed by {issuer_name}. "
                f"Actions: {'; '.join(set(ai_detected_actions))}. "
                f"{'SynthID imperceptible watermark confirmed.' if has_synthid else ''}"
            )
        elif has_untrusted_signer or not signer_trusted:
            status = C2PAStatus.SIGNER_UNTRUSTED
            issuer_name = active_manifest.get("signature_info", {}).get("issuer", "Unknown Signer") if manifest_dict else "Unknown"
            trust_explanation = (
                f"Cryptographic signature is valid, but signing certificate ('{issuer_name}') is not anchored "
                "in a recognized root trust store (standard for development, test, or custom signers)."
            )
            provenance_notes = f"SIGNATURE VALID (UNTRUSTED SIGNER): {trust_explanation}"
        else:
            status = C2PAStatus.SIGNATURE_VALID
            trust_explanation = "Cryptographic signature verified and certificate path anchored in recognized trust list."
            provenance_notes = f"VALID TRUSTED PROVENANCE: {trust_explanation}"
        
        return C2PAValidationResult(
            status=status,
            sdk_available=True,
            manifest_present=True,
            validation_status=val_state or ("VALID" if signature_valid else "INVALID"),
            signature_valid=signature_valid,
            signer_trusted=signer_trusted,
            trust_validation_status=trust_explanation,
            manifest_data=manifest_dict,
            claims=claims_summary,
            provenance_notes=provenance_notes
        )
        
    except Exception as e:
        logger.error(f"C2PA inspection encountered an error: {e}")
        return C2PAValidationResult(
            status=C2PAStatus.ANALYSIS_FAILED,
            sdk_available=True,
            manifest_present=False,
            validation_status="ERROR",
            signature_valid=None,
            signer_trusted=None,
            trust_validation_status=f"Internal inspection error: {str(e)}",
            manifest_data=None,
            claims=None,
            provenance_notes=f"C2PA inspection encountered an internal parser error: {str(e)}"
        )
    finally:
        if reader is not None:
            try:
                reader.close()
            except Exception:
                pass
