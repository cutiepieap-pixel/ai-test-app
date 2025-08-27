# app_kb_chat.py  (LOCAL + CLOUD READY)
# - Local: uses AWS_PROFILE if set
# - Cloud (App Runner etc.): uses instance role (no profile)
# - REGION/KB_ID/MODEL_ID overridable via env vars
# - Sonnet-4 via Inference Profile (auto-resolve, env override supported)
# - STS identity shown only on errors for simpler happy path

import os
from functools import lru_cache
import boto3

# ===== Runtime config (환경변수로 덮어쓰기 가능) =====
PROFILE   = os.getenv("AWS_PROFILE", "")                 # 로컬이면 aws configure --profile 값
REGION    = os.getenv("AWS_REGION",  "us-east-1")        # KB/모델 리전
KB_ID     = os.getenv("KB_ID",       "WU69M0JTMY")       # ★ 로컬/계정에 맞는 KB ID로 교체 권장
MODEL_ID  = os.getenv("MODEL_ID",    "anthropic.claude-sonnet-4-20250514-v1:0")
# 필요 시 인퍼런스 프로파일을 직접 고정(명시)하고 싶다면 아래 환경변수를 설정
INFERENCE_PROFILE_ARN = os.getenv("INFERENCE_PROFILE_ARN", "")
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "20"))

# ===== Minimal message class =====
class ChatMessage:
    def __init__(self, role, text):
        self.role = role
        self.text = text

def convert_chat_messages_to_converse_api(chat_messages):
    return [{"role": m.role, "content": [{"text": m.text}]} for m in chat_messages]

# ===== boto3 session & clients =====
@lru_cache(maxsize=1)
def _session():
    # 로컬: 프로필이 있으면 사용, 클라우드: 인스턴스 역할(프로필 없이)
    if PROFILE:
        return boto3.Session(profile_name=PROFILE, region_name=REGION)
    return boto3.Session(region_name=REGION)

@lru_cache(maxsize=1)
def _brt():
    return _session().client("bedrock-runtime")

@lru_cache(maxsize=1)
def _br_agent_rt():
    return _session().client("bedrock-agent-runtime")

@lru_cache(maxsize=1)
def _br_agent():
    return _session().client("bedrock")

@lru_cache(maxsize=1)
def _br_kb_ctrl():
    return _session().client("bedrock-agent")

@lru_cache(maxsize=1)
def _sts():
    return _session().client("sts")

def _caller_identity_safe():
    try:
        i = _sts().get_caller_identity()
        return f"account={i.get('Account')} arn={i.get('Arn')}"
    except Exception as e:
        return f"(caller identity lookup failed: {type(e).__name__}: {e})"

# ===== Inference Profile resolver (Sonnet-4 등) =====
@lru_cache(maxsize=2)
def resolve_inference_profile_arn(model_id: str) -> str:
    # 1) 환경변수로 명시된 ARN 우선
    if INFERENCE_PROFILE_ARN:
        return INFERENCE_PROFILE_ARN

    # 2) 현재 계정/리전에서 자동 탐색
    br = _br_agent()  # bedrock control-plane
    summaries = br.list_inference_profiles().get("inferenceProfileSummaries", [])
    # 시스템 정의 우선, 그 다음 앱 프로파일
    ordered = sorted(summaries, key=lambda p: (p.get("type") != "SYSTEM_DEFINED", p.get("name", "")))
    for p in ordered:
        detail = br.get_inference_profile(inferenceProfileIdentifier=p["inferenceProfileArn"])
        for m in detail.get("models", []):
            if model_id in (m.get("modelArn") or ""):
                return detail["inferenceProfileArn"]
    raise RuntimeError(f"No inference profile contains '{model_id}' in {REGION} (profile='{PROFILE or 'instance-role'}').")

# ===== Core: chat with a foundation model (Converse) =====
def chat_with_model(message_history, new_text: str):
    # update history
    message_history.append(ChatMessage("user", new_text))
    if len(message_history) > MAX_MESSAGES:
        del message_history[0 : len(message_history) - MAX_MESSAGES]

    ip_arn = resolve_inference_profile_arn(MODEL_ID)

    try:
        resp = _brt().converse(
            inferenceProfileArn=ip_arn,                # 모델 ID 대신 인퍼런스 프로파일 사용
            messages=convert_chat_messages_to_converse_api(message_history),
            inferenceConfig={"maxTokens": 2000, "temperature": 0, "topP": 0.9, "stopSequences": []},
        )
        output = resp["output"]["message"]["content"][0]["text"]
    except Exception as e:
        ident = _caller_identity_safe()
        output = f"Error during converse: {type(e).__name__}: {e}\n↳ identity: {ident}\n↳ region={REGION}, profile={PROFILE or 'instance-role'}"

    message_history.append(ChatMessage("assistant", output))
    return output

# ===== Core: chat with Knowledge Base (RetrieveAndGenerate) =====
def chat_with_kb(message_history, new_text: str):
    # update history
    message_history.append(ChatMessage("user", new_text))
    if len(message_history) > MAX_MESSAGES:
        del message_history[0 : len(message_history) - MAX_MESSAGES]

    ip_arn = resolve_inference_profile_arn(MODEL_ID)

    prompt = (
        "You are a question answering agent.\n"
        "Use only the provided search results to answer the user's question.\n"
        "If results are insufficient, say you couldn't find an exact answer.\n"
        "Double-check user assertions against the results.\n"
        "Answer in the user's language.\n\n"
        "Search results (numbered):\n$search_results$\n\n"
        "$output_format_instructions$"
    )

    kb_rt = _br_agent_rt()
    kb_ctl = _br_kb_ctrl()

    try:
        resp = kb_rt.retrieve_and_generate(
            input={"text": new_text},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": KB_ID,      # 현재 계정/리전의 유효한 KB ID여야 함
                    "modelArn": ip_arn,            # 인퍼런스 프로파일 ARN
                    "retrievalConfiguration": {
                        "vectorSearchConfiguration": {
                            "overrideSearchType": "HYBRID",
                            "numberOfResults": 5
                        }
                    },
                    "generationConfiguration": {
                        "promptTemplate": {"textPromptTemplate": prompt},
                        "inferenceConfig": {
                            "textInferenceConfig": {
                                "temperature": 0,
                                "topP": 0.7,
                                "maxTokens": 1024
                            }
                        }
                    }
                }
            }
        )
        output = resp["output"]["text"]

    except kb_rt.exceptions.ResourceNotFoundException:
        # 계정/리전에서 KB 목록을 보여주어 교정에 도움
        try:
            lst = kb_ctl.list_knowledge_bases().get("knowledgeBaseSummaries", [])
            kb_list = "\n".join(
                f"- {kb['knowledgeBaseId']} | {kb.get('name','')} | {kb.get('status','')}"
                for kb in lst
            ) or "(none)"
        except Exception as e2:
            kb_list = f"(KB list failed: {type(e2).__name__}: {e2})"
        ident = _caller_identity_safe()
        output = (
            "⚠️ Knowledge Base not found.\n"
            f"- Provided KB_ID: {KB_ID}\n"
            f"- Region: {REGION}\n"
            f"- {ident}\n"
            f"- KBs in this account/region:\n{kb_list}\n"
            "→ Replace KB_ID with a valid one in this account/region."
        )

    except kb_rt.exceptions.AccessDeniedException as e:
        output = (
            f"AccessDenied: {e}\n"
            "→ Ensure caller has: bedrock-agent-runtime:RetrieveAndGenerate, "
            "bedrock-agent:GetKnowledgeBase, bedrock-agent:ListKnowledgeBases, and access to data sources (e.g., S3)."
        )

    except Exception as e:
        ident = _caller_identity_safe()
        output = f"Error during retrieve_and_generate: {type(e).__name__}: {e}\n↳ identity: {ident}\n↳ region={REGION}, profile={PROFILE or 'instance-role'}"

    message_history.append(ChatMessage("assistant", output))
    return output

# ===== Optional: quick diagnostics =====
def debug_print_identity_and_kbs():
    print(f"[Region] {REGION}, [Profile] {PROFILE or 'instance-role'}")
    try:
        ident = _caller_identity_safe()
        print(f"[Identity] {ident}")
    except Exception as e:
        print(f"[Identity error] {type(e).__name__}: {e}")

    try:
        ip_arn = resolve_inference_profile_arn(MODEL_ID)
        print(f"[InferenceProfile for {MODEL_ID}] {ip_arn}")
    except Exception as e:
        print(f"[IP resolve error] {type(e).__name__}: {e}")

    try:
        lst = _br_kb_ctrl().list_knowledge_bases().get("knowledgeBaseSummaries", [])
        print("[KBs in region]:")
        for kb in lst:
            print(f"  - {kb['knowledgeBaseId']} | {kb.get('name','')} | {kb.get('status','')}")
    except Exception as e:
        print(f"[KB list error] {type(e).__name__}: {e}")
