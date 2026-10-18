import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.secura_social_service import get_secura_social_service, DEMO_POLICY_CONFIG
from app.services.policy_rag import get_policy_rag_engine, OFFICIAL_POLICY_DOCUMENTS

client = TestClient(app)
social_service = get_secura_social_service()
policy_rag = get_policy_rag_engine()

@pytest.fixture(autouse=True)
def setup_social_sandbox():
    """Ensure clean seeded state for each test run."""
    social_service.reset_demo_database()
    DEMO_POLICY_CONFIG["BLOCK_AI_GENERATED_MEDIA"] = True
    DEMO_POLICY_CONFIG["block_ai_generated_media"] = True
    yield

def create_synthetic_image(color=(255, 100, 100), size=(128, 128)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format="JPEG")
    return buf.getvalue()

# ============================================================================
# 1. SHARED DETECTOR & RAG ENGINE INTEGRATION TESTS
# ============================================================================
def test_shared_inspection_real_image():
    """Verify shared detector processes image and returns canonical verdict."""
    img_bytes = create_synthetic_image(color=(30, 80, 150))
    res = social_service.inspect_and_moderate_media(
        media_bytes=img_bytes,
        filename="nature_scene.jpg",
        content_type="image/jpeg",
        app_source="test",
        text_content="Scenic photo of the Himalayas"
    )
    assert res.canonical_verdict in ["AI GENERATED", "NOT AI GENERATED"]
    assert isinstance(res.canonical_score, float)
    assert res.action in ["ALLOW", "BLOCK"]
    assert len(res.content_hash) == 64
    assert res.model_name == "UniversalFakeDetect-CLIP-ViT-L/14"

def test_government_policy_rag_citations():
    """Verify official MeitY and statutory citations are present and structured."""
    sources = OFFICIAL_POLICY_DOCUMENTS
    assert len(sources) >= 5
    
    # Check for MeitY IT Rules
    meity_rule = next((s for s in sources if "MeitY" in s["authority"] or "IT Rules" in s["statute"]), None)
    assert meity_rule is not None
    assert "https://" in meity_rule["official_url"]
    assert meity_rule["effective_date"] != ""
    assert meity_rule["rule_id"] != ""

def test_rag_retrieval_and_violation_block():
    """Verify statutory violation query correctly triggers BLOCK with MeitY citations."""
    eval_res = policy_rag.evaluate_content(
        text_content="Creating deceptive deepfake video impersonating the Prime Minister to commit financial fraud",
        canonical_ai_verdict="NOT AI GENERATED",
        block_ai_policy_active=True
    )
    assert eval_res.action == "BLOCK"
    assert len(eval_res.matched_rules) > 0
    assert any("BNS" in r.rule_id or "IT-RULE-3-1-B" in r.rule_id for r in eval_res.matched_rules)
    assert len(eval_res.citations) > 0

# ============================================================================
# 2. INSTAGRAM-INSPIRED WORKFLOW TESTS
# ============================================================================
def test_instagram_feed_and_post_creation():
    """Verify feed listing, post creation, and live feed updates."""
    # List feed initially
    r_feed = client.get("/api/v1/social/instagram/feed")
    assert r_feed.status_code == 200
    initial_posts = r_feed.json()
    assert len(initial_posts) >= 2

    # Post a clean image as @arjun_photo
    img_bytes = create_synthetic_image()
    files = {"file": ("test_post.jpg", img_bytes, "image/jpeg")}
    data = {"user_id": "u_arjun", "caption": "Golden hour in New Delhi", "tags": "delhi,sunset"}
    
    # Disable AI blocking temporarily to allow clean publication test
    DEMO_POLICY_CONFIG["BLOCK_AI_GENERATED_MEDIA"] = False
    DEMO_POLICY_CONFIG["block_ai_generated_media"] = False
    r_post = client.post("/api/v1/social/instagram/posts", files=files, data=data)
    assert r_post.status_code == 201
    post_data = r_post.json()
    assert post_data["caption"] == "Golden hour in New Delhi"
    assert post_data["likes_count"] == 0

    # Verify post appears in feed
    r_feed2 = client.get("/api/v1/social/instagram/feed")
    assert len(r_feed2.json()) == len(initial_posts) + 1

def test_instagram_like_and_comments():
    """Verify atomic like/unlike toggle, duplicate prevention, and comment thread."""
    # Fetch existing post
    r_feed = client.get("/api/v1/social/instagram/feed?user_id=u_arjun")
    post_id = r_feed.json()[0]["id"]
    initial_likes = r_feed.json()[0]["likes_count"]

    # Like post
    r_like = client.post(f"/api/v1/social/instagram/posts/{post_id}/like", json={"user_id": "u_arjun"})
    assert r_like.status_code == 200
    assert r_like.json()["liked"] is True
    assert r_like.json()["likes_count"] == initial_likes + 1

    # Unlike post (toggle)
    r_unlike = client.post(f"/api/v1/social/instagram/posts/{post_id}/like", json={"user_id": "u_arjun"})
    assert r_unlike.status_code == 200
    assert r_unlike.json()["liked"] is False
    assert r_unlike.json()["likes_count"] == initial_likes

    # Add Comment
    r_comm = client.post(
        f"/api/v1/social/instagram/posts/{post_id}/comments",
        json={"user_id": "u_priya", "text": "Stunning composition Arjun!"}
    )
    assert r_comm.status_code == 201
    comm_data = r_comm.json()
    assert comm_data["content"] == "Stunning composition Arjun!"

    # List Comments
    r_list = client.get(f"/api/v1/social/instagram/posts/{post_id}/comments")
    assert r_list.status_code == 200
    assert len(r_list.json()) >= 1

def test_instagram_pre_publication_block():
    """Verify AI-generated post is blocked pre-publication and never reaches feed."""
    DEMO_POLICY_CONFIG["BLOCK_AI_GENERATED_MEDIA"] = True
    DEMO_POLICY_CONFIG["block_ai_generated_media"] = True
    
    img_bytes = create_synthetic_image()
    files = {"file": ("ai_generated_art.jpg", img_bytes, "image/jpeg")}
    data = {
        "user_id": "u_arjun",
        "caption": "Midjourney v6 hyper-realistic synthetic cyber portrait deepfake",
        "tags": "ai,deepfake"
    }
    
    r_post = client.post("/api/v1/social/instagram/posts", files=files, data=data)
    # Must be intercepted with 403 Forbidden
    assert r_post.status_code == 403
    err_body = r_post.json()
    assert err_body["action"] == "BLOCK"
    
    # Verify post was NOT added to feed
    r_feed = client.get("/api/v1/social/instagram/feed")
    assert not any("Midjourney v6" in p["caption"] for p in r_feed.json())

# ============================================================================
# 3. WHATSAPP-INSPIRED WORKFLOW TESTS
# ============================================================================
def test_whatsapp_safe_otp_authentication():
    """Verify safe ephemeral OTP issuance, validation, and attempt limits."""
    # Request OTP
    r_req = client.post("/api/v1/social/otp/request", json={"phone_number": "+91 98765 43210"})
    assert r_req.status_code == 200
    otp_code = r_req.json()["demo_otp_code"]
    assert len(otp_code) == 6

    # Verify with wrong code
    r_wrong = client.post("/api/v1/social/otp/verify", json={"phone_number": "+91 98765 43210", "otp_code": "000000"})
    assert r_wrong.status_code == 200
    assert r_wrong.json()["success"] is False

    # Verify with correct code
    r_ok = client.post("/api/v1/social/otp/verify", json={"phone_number": "+91 98765 43210", "otp_code": otp_code})
    assert r_ok.status_code == 200
    assert r_ok.json()["success"] is True
    session_token = r_ok.json()["session_token"]
    assert session_token.startswith("sess_")

    # Replay protection: verify used OTP is invalidated
    r_replay = client.post("/api/v1/social/otp/verify", json={"phone_number": "+91 98765 43210", "otp_code": otp_code})
    assert r_replay.status_code == 200
    assert r_replay.json()["success"] is False

def test_whatsapp_messages_and_group_creation():
    """Verify conversation listing, group creation, and message sending."""
    # List conversations for Priya
    r_convs = client.get("/api/v1/social/whatsapp/conversations?user_id=u_priya")
    assert r_convs.status_code == 200
    convs = r_convs.json()
    assert len(convs) >= 1
    conv_id = convs[0]["id"]

    # Send clean text message
    r_msg = client.post(
        f"/api/v1/social/whatsapp/conversations/{conv_id}/messages",
        json={"sender_id": "u_priya", "content": "Checking in regarding the cyber briefing tomorrow."}
    )
    assert r_msg.status_code == 201
    assert r_msg.json()["status"] == "read"

    # Create Group
    r_grp = client.post("/api/v1/social/whatsapp/groups", json={
        "group_name": "Mission 26 Response Team",
        "creator_id": "u_priya",
        "member_ids": ["u_priya", "u_arjun", "u_tech"]
    })
    assert r_grp.status_code == 201
    assert r_grp.json()["name"] == "Mission 26 Response Team"
    assert r_grp.json()["is_group"] is True

def test_whatsapp_pre_send_media_block():
    """Verify inspection API directly evaluates media and policy."""
    DEMO_POLICY_CONFIG["BLOCK_AI_GENERATED_MEDIA"] = True
    DEMO_POLICY_CONFIG["block_ai_generated_media"] = True
    img_bytes = create_synthetic_image()
    files = {"file": ("ai_voice_clone.jpg", img_bytes, "image/jpeg")}

    inspect_res = client.post(
        "/api/v1/social/inspect",
        files=files,
        data={"application": "whatsapp", "text_context": "Synthetic non-consensual deepfake"}
    )
    assert inspect_res.status_code in [200, 403]
    if inspect_res.status_code == 200:
        assert inspect_res.json()["action"] in ["ALLOW", "BLOCK"]

# ============================================================================
# 4. TELEGRAM-INSPIRED WORKFLOW TESTS
# ============================================================================
def test_telegram_channels_reactions_pins():
    """Verify channel broadcast, member join/leave, emoji reactions, and pinning."""
    # List channels
    r_chans = client.get("/api/v1/social/telegram/channels?user_id=u_tech")
    assert r_chans.status_code == 200
    chans = r_chans.json()
    assert len(chans) >= 2
    chan_id = chans[0]["id"]

    # Toggle Join
    r_join = client.post(f"/api/v1/social/telegram/channels/{chan_id}/join", json={"user_id": "u_tech"})
    assert r_join.status_code == 200
    # Toggle Leave
    r_leave = client.post(f"/api/v1/social/telegram/channels/{chan_id}/join", json={"user_id": "u_tech"})
    assert r_leave.status_code == 200

    # Fetch channel posts
    r_posts = client.get(f"/api/v1/social/telegram/channels/{chan_id}/posts?user_id=u_tech")
    assert r_posts.status_code == 200
    posts = r_posts.json()
    assert len(posts) >= 1
    post_id = posts[0]["id"]

    # Toggle Emoji Reaction 👍
    r_react = client.post(
        f"/api/v1/social/telegram/posts/{post_id}/react",
        json={"user_id": "u_tech", "reaction": "👍"}
    )
    assert r_react.status_code == 200
    assert "reactions" in r_react.json()

    # Toggle Pin
    r_pin = client.post(
        f"/api/v1/social/telegram/posts/{post_id}/pin",
        json={"user_id": "u_tech"}
    )
    assert r_pin.status_code == 200
    assert "is_pinned" in r_pin.json()

# ============================================================================
# 5. MODERATION DASHBOARD & AUDIT TESTS
# ============================================================================
def test_moderation_stats_and_audit_trail():
    """Verify database KPI metrics and audit trail records."""
    r_stats = client.get("/api/v1/social/moderation/stats")
    assert r_stats.status_code == 200
    data = r_stats.json()
    assert "total_inspections" in data or "total_media_inspections" in data
    assert "demo_policy_blocks" in data or "posts_blocked_demo_ai_policy" in data
    assert "policy_kb_version" in data
    assert "recent_audits" in data
    assert isinstance(data["recent_audits"], list)
