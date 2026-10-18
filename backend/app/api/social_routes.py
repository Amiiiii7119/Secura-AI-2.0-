# Secura Social API Endpoints (Instagram, WhatsApp, Telegram, RAG & Moderation)

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.services.policy_rag import OFFICIAL_POLICY_DOCUMENTS, get_policy_rag_engine
from app.services.secura_social_service import (
    DEMO_POLICY_CONFIG,
    MEDIA_UPLOAD_DIR,
    get_db_connection,
    get_secura_social_service,
)

logger = logging.getLogger(__name__)

social_router = APIRouter(prefix="/social", tags=["Secura Social Demonstration Suite"])


# -------------------------------------------------------------
# Pydantic Request Models
# -------------------------------------------------------------
class RequestOTPPayload(BaseModel):
    phone_number: str = Field(..., description="Demo phone number (e.g. +91 98765 43210)")


class VerifyOTPPayload(BaseModel):
    phone_number: str
    otp_code: str


class TogglePolicyPayload(BaseModel):
    enabled: bool


class QueryPolicyPayload(BaseModel):
    query: str


class LikePostPayload(BaseModel):
    user_id: str


class CommentPostPayload(BaseModel):
    user_id: str
    text: str


class FollowUserPayload(BaseModel):
    follower_id: str


class CreateGroupPayload(BaseModel):
    creator_id: str
    group_name: str
    member_ids: List[str]


class CreateChannelPayload(BaseModel):
    creator_id: str
    name: str
    handle: str
    description: Optional[str] = ""


class ReactPayload(BaseModel):
    target_type: str  # message or channel_post
    target_id: str
    user_id: str
    emoji: str


# -------------------------------------------------------------
# 1. System, Policy & Media File Serving
# -------------------------------------------------------------
@social_router.get("/policy/config")
async def get_policy_config():
    """Retrieve active demo policy status and knowledge-base metadata."""
    return {
        "success": True,
        "config": DEMO_POLICY_CONFIG,
        "total_official_rules": len(OFFICIAL_POLICY_DOCUMENTS),
        "policy_kb_version": "2026.1-IN-GOV"
    }


@social_router.post("/policy/toggle")
async def toggle_demo_policy(payload: TogglePolicyPayload):
    """Toggle BLOCK_AI_GENERATED_MEDIA demo policy dynamically."""
    DEMO_POLICY_CONFIG["BLOCK_AI_GENERATED_MEDIA"] = payload.enabled
    return {
        "success": True,
        "active_policy": "BLOCK_AI_GENERATED_MEDIA",
        "enabled": DEMO_POLICY_CONFIG["BLOCK_AI_GENERATED_MEDIA"],
        "message": f"Demo policy BLOCK_AI_GENERATED_MEDIA is now {'ENABLED' if payload.enabled else 'DISABLED'}."
    }


@social_router.get("/policy/knowledge-base")
async def get_policy_knowledge_base():
    """List all verified Indian Government statutory rules and platform policies."""
    return {
        "success": True,
        "policy_version": "2026.1-IN-GOV",
        "rules": OFFICIAL_POLICY_DOCUMENTS
    }


@social_router.post("/policy/query")
async def query_policy_rag(payload: QueryPolicyPayload):
    """Query the Government Policy RAG engine directly with sample caption/message text."""
    engine = get_policy_rag_engine()
    matches = engine.query_policy(payload.query)
    return {
        "success": True,
        "query": payload.query,
        "matched_rules": [m.dict() for m in matches]
    }


@social_router.get("/media/{filename}")
async def serve_media(filename: str):
    """Serve uploaded media files safely."""
    clean_name = Path(filename).name
    file_path = MEDIA_UPLOAD_DIR / clean_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")
    media_type = "image/jpeg" if clean_name.endswith((".jpg", ".jpeg")) else "video/mp4"
    return FileResponse(file_path, media_type=media_type)


@social_router.post("/reset-demo")
async def reset_demo_database():
    """Reset demo database tables to seed baseline."""
    svc = get_secura_social_service()
    return svc.reset_demo_database()


@social_router.post("/inspect-media")
async def inspect_media_precheck(
    file: UploadFile = File(...),
    app_source: str = Form("instagram"),
    user_id: Optional[str] = Form(None),
    caption: Optional[str] = Form("")
):
    """Standalone pre-check endpoint running genuine Secura detection & policy evaluation."""
    data = await file.read()
    svc = get_secura_social_service()
    u_id = user_id if (user_id and isinstance(user_id, str) and not hasattr(user_id, 'default')) else None
    src = app_source if (app_source and isinstance(app_source, str) and not hasattr(app_source, 'default')) else "instagram"
    txt = caption if (caption and isinstance(caption, str) and not hasattr(caption, 'default')) else ""
    dec = svc.inspect_and_moderate_media(
        media_bytes=data,
        filename=file.filename or "media.jpg",
        app_source=src,
        user_id=u_id,
        text_content=txt,
        content_type=file.content_type
    )
    return dec.dict()


# -------------------------------------------------------------
# 2. Users & Demo Authentication
# -------------------------------------------------------------
@social_router.get("/users")
async def get_social_users():
    """List all demo accounts for testing across Instagram, WhatsApp, and Telegram."""
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM social_users ORDER BY username ASC").fetchall()
        return [dict(r) for r in rows]


@social_router.post("/auth/request-otp")
@social_router.post("/otp/request")
async def request_otp(payload: RequestOTPPayload):
    """Safe demo OTP request for WhatsApp demo simulation."""
    svc = get_secura_social_service()
    return svc.request_demo_otp(payload.phone_number)


@social_router.post("/auth/verify-otp")
@social_router.post("/otp/verify")
async def verify_otp(payload: VerifyOTPPayload):
    """Safe demo OTP verification."""
    svc = get_secura_social_service()
    res = svc.verify_demo_otp(payload.phone_number, payload.otp_code)
    return res


# -------------------------------------------------------------
# 3. Application A: Instagram-Inspired Endpoints
# -------------------------------------------------------------
@social_router.get("/instagram/feed")
async def get_instagram_feed(user_id: Optional[str] = Query(None)):
    """Retrieve chronological feed of verified published posts."""
    svc = get_secura_social_service()
    return svc.get_instagram_feed(current_user_id=user_id)


@social_router.post("/instagram/posts", status_code=status.HTTP_201_CREATED)
async def create_instagram_post(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    caption: str = Form(""),
    tags: str = Form("")
):
    """Create post with mandatory pre-publication AI detection and policy check."""
    media_data = await file.read()
    svc = get_secura_social_service()
    res = svc.create_instagram_post(
        user_id=user_id,
        media_bytes=media_data,
        filename=file.filename or "post.jpg",
        caption=caption,
        tags=tags
    )
    if not res.get("success"):
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=res)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=res)


@social_router.post("/instagram/posts/{post_id}/like")
async def toggle_like(post_id: str, payload: LikePostPayload):
    svc = get_secura_social_service()
    return svc.toggle_like(post_id, payload.user_id)


@social_router.get("/instagram/posts/{post_id}/comments")
async def list_comments(post_id: str):
    svc = get_secura_social_service()
    return svc.get_post_comments(post_id)


@social_router.post("/instagram/posts/{post_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(post_id: str, payload: CommentPostPayload):
    svc = get_secura_social_service()
    res = svc.add_comment(post_id, payload.user_id, payload.text)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Comment rejected"))
    comm = res.get("comment", {})
    comm["content"] = comm.get("text", payload.text)
    comm["text"] = comm.get("text", payload.text)
    return comm


@social_router.delete("/instagram/posts/{post_id}/comments/{comment_id}")
async def delete_comment(post_id: str, comment_id: str, user_id: str = Query(...)):
    svc = get_secura_social_service()
    success = svc.delete_comment(comment_id, user_id)
    return {"success": success}


@social_router.delete("/instagram/posts/{post_id}")
async def delete_post(post_id: str, user_id: str = Query(...)):
    svc = get_secura_social_service()
    success = svc.delete_post(post_id, user_id)
    return {"success": success}


@social_router.post("/instagram/follow/{target_user_id}")
async def toggle_follow(target_user_id: str, payload: FollowUserPayload):
    svc = get_secura_social_service()
    return svc.toggle_follow(payload.follower_id, target_user_id)


@social_router.get("/instagram/profile/{username}")
async def get_user_profile(username: str, viewer_id: Optional[str] = Query(None)):
    svc = get_secura_social_service()
    prof = svc.get_user_profile(username, current_user_id=viewer_id)
    if not prof:
        raise HTTPException(status_code=404, detail="User profile not found")
    return prof


# -------------------------------------------------------------
# 4. Application B: WhatsApp-Inspired Endpoints
# -------------------------------------------------------------
@social_router.get("/whatsapp/conversations")
async def get_conversations(user_id: str = Query(...)):
    svc = get_secura_social_service()
    return svc.get_whatsapp_conversations(user_id)


@social_router.get("/whatsapp/conversations/{conv_id}/messages")
async def get_messages(conv_id: str, user_id: str = Query(...)):
    svc = get_secura_social_service()
    return svc.get_conversation_messages(conv_id, user_id)


@social_router.post("/whatsapp/conversations/{conv_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_whatsapp_message(
    conv_id: str,
    request: Request,
    sender_id: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    reply_to_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """Send WhatsApp message with pre-send media inspection (supports JSON or multipart)."""
    svc = get_secura_social_service()
    ct = request.headers.get("content-type", "")
    if "application/json" in ct:
        body = await request.json()
        s_id = body.get("sender_id") or body.get("user_id") or "u_arjun"
        msg_text = body.get("content") or body.get("text") or ""
        rep_id = body.get("reply_to_id")
        res = svc.send_whatsapp_message(
            conversation_id=conv_id,
            sender_id=s_id,
            text=msg_text,
            media_bytes=None,
            filename=None,
            reply_to_id=rep_id
        )
        if not res.get("success") and res.get("blocked"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=res)
        return res

    media_bytes = None
    filename = None
    if file and file.filename:
        media_bytes = await file.read()
        filename = file.filename

    s_id = sender_id or "u_arjun"
    res = svc.send_whatsapp_message(
        conversation_id=conv_id,
        sender_id=s_id,
        text=text,
        media_bytes=media_bytes,
        filename=filename,
        reply_to_id=reply_to_id
    )
    if not res.get("success") and res.get("blocked"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=res)
    return res


@social_router.post("/whatsapp/groups", status_code=status.HTTP_201_CREATED)
async def create_group(payload: CreateGroupPayload):
    svc = get_secura_social_service()
    return svc.create_whatsapp_group(payload.creator_id, payload.group_name, payload.member_ids)


# -------------------------------------------------------------
# 5. Application C: Telegram-Inspired Endpoints
# -------------------------------------------------------------
@social_router.get("/telegram/channels")
async def get_channels(user_id: str = Query(...)):
    svc = get_secura_social_service()
    return svc.get_telegram_channels(user_id)


@social_router.post("/telegram/channels")
async def create_channel(payload: CreateChannelPayload):
    now_str = datetime.now(timezone.utc).isoformat()
    ch_id = f"ch_{secrets.token_hex(6)}"
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO social_channels VALUES (?, ?, ?, ?, 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=150', ?, ?)",
            (ch_id, payload.name, payload.handle, payload.description, payload.creator_id, now_str)
        )
        conn.execute("INSERT INTO social_channel_members VALUES (?, ?, 'admin', ?)", (ch_id, payload.creator_id, now_str))
        conn.commit()
    return {"success": True, "channel_id": ch_id, "name": payload.name, "handle": payload.handle}


@social_router.get("/telegram/channels/{channel_id}/posts")
async def get_channel_posts(channel_id: str, user_id: str = Query(...)):
    svc = get_secura_social_service()
    return svc.get_channel_posts(channel_id, user_id)


@social_router.post("/telegram/channels/{channel_id}/posts")
async def publish_channel_post(
    channel_id: str,
    sender_id: str = Form(...),
    text: Optional[str] = Form(None),
    is_pinned: bool = Form(False),
    file: Optional[UploadFile] = File(None)
):
    """Publish to Telegram channel with mandatory pre-publication inspection."""
    svc = get_secura_social_service()
    media_bytes = None
    filename = None
    if file:
        media_bytes = await file.read()
        filename = file.filename

    res = svc.publish_channel_post(
        channel_id=channel_id,
        sender_id=sender_id,
        text=text,
        media_bytes=media_bytes,
        filename=filename,
        is_pinned=is_pinned
    )
    if not res["success"]:
        return JSONResponse(status_code=403, content=res)
    return res


@social_router.post("/telegram/channels/{channel_id}/membership")
async def toggle_channel_membership(channel_id: str, user_id: str = Query(...)):
    svc = get_secura_social_service()
    return svc.toggle_channel_membership(channel_id, user_id)


@social_router.post("/telegram/react")
async def react_to_item(payload: ReactPayload):
    svc = get_secura_social_service()
    return svc.react_to_item(payload.target_type, payload.target_id, payload.user_id, payload.emoji)


# -------------------------------------------------------------
# 6. Admin Moderation Dashboard Endpoints
# -------------------------------------------------------------
@social_router.get("/moderation/stats")
async def get_moderation_stats():
    """Retrieve real-time database counts, model status, and policy stats."""
    svc = get_secura_social_service()
    return svc.get_moderation_stats()


@social_router.get("/moderation/history")
async def get_moderation_history(
    app_source: Optional[str] = Query("all"),
    action: Optional[str] = Query("all"),
    limit: int = Query(50, ge=1, le=200)
):
    """Retrieve detailed audit history of moderation decisions."""
    svc = get_secura_social_service()
    return svc.get_moderation_history(app_source=app_source, action=action, limit=limit)

# ============================================================================
# ALIASES FOR MISSION 26 SUITE COMPLIANCE
# ============================================================================

@social_router.post("/inspect")
async def inspect_media_alias(
    file: UploadFile = File(...),
    application: str = Form("instagram"),
    text_context: Optional[str] = Form(None)
):
    return await inspect_media_precheck(file=file, app_source=application, caption=text_context or "")

@social_router.post("/otp/request")
async def request_otp_alias(body: Dict[str, str]):
    phone = body.get("phone_number", "")
    return await request_otp(RequestOTPPayload(phone_number=phone))

@social_router.post("/otp/verify")
async def verify_otp_alias(body: Dict[str, str]):
    phone = body.get("phone_number", "")
    otp = body.get("otp_code", "")
    return await verify_otp(VerifyOTPPayload(phone_number=phone, otp_code=otp))

@social_router.post("/telegram/channels/{channel_id}/join")
async def join_channel_alias(channel_id: str, body: Dict[str, str]):
    user_id = body.get("user_id", "")
    return await toggle_channel_membership(channel_id=channel_id, user_id=user_id)

@social_router.post("/telegram/posts/{post_id}/react")
async def react_post_alias(post_id: str, body: Dict[str, str]):
    emoji = body.get("reaction") or body.get("emoji") or "👍"
    user_id = body.get("user_id", "")
    payload = ReactPayload(target_type="channel_post", target_id=post_id, user_id=user_id, emoji=emoji)
    return await react_to_item(payload)

@social_router.post("/telegram/posts/{post_id}/pin")
def pin_post_endpoint(post_id: str, body: Dict[str, str]):
    with get_db_connection() as conn:
        curr = conn.execute("SELECT is_pinned FROM social_channel_posts WHERE id = ?", (post_id,)).fetchone()
        if not curr:
            raise HTTPException(status_code=404, detail="Post not found")
        new_state = 0 if curr[0] else 1
        conn.execute("UPDATE social_channel_posts SET is_pinned = ? WHERE id = ?", (new_state, post_id))
        conn.commit()
        return {"status": "success", "post_id": post_id, "is_pinned": bool(new_state)}

@social_router.post("/whatsapp/conversations/{conv_id}/media")
async def send_whatsapp_media_endpoint(
    conv_id: str,
    file: UploadFile = File(...),
    sender_id: str = Form(...),
):
    svc = get_secura_social_service()
    file_bytes = await file.read()
    content_type = file.content_type or "image/jpeg"
    mod_result = svc.inspect_and_moderate_media(
        media_bytes=file_bytes,
        filename=file.filename or "media.jpg",
        content_type=content_type,
        app_source="whatsapp"
    )
    if mod_result.action == "BLOCK":
        return JSONResponse(
            status_code=403,
            content={
                "detail": f"Media send blocked: {mod_result.explanation}",
                "action": "BLOCK",
                "canonical_verdict": mod_result.canonical_verdict,
                "raw_score": mod_result.canonical_score,
                "explanation": mod_result.explanation,
                "citations": [c.model_dump() if hasattr(c, "model_dump") else c for c in mod_result.citations]
            }
        )
    return svc.send_message(
        conversation_id=conv_id,
        sender_id=sender_id,
        content=f"Sent attachment: {file.filename}",
        media_bytes=file_bytes,
        filename=file.filename,
        media_type="video" if "video" in content_type else "image"
    )

@social_router.post("/demo/reset")
async def reset_demo_alias():
    return await reset_demo_database()
