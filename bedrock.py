# bedrock.py  (cloud-ready: no local profile dependency)
import os
from functools import lru_cache
import boto3

# ========= Runtime config (env-overridable) =========
REGION    = os.getenv("AWS_REGION", "us-east-1")
KB_ID     = os.getenv("KB_ID", "WU69M0JTMY")  # ← 필요하면 App Runner 환경변수에 설정
MODEL_ID  = os.getenv("MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0")
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "20"))

# ========= Message model =========
class ChatMessage:
    def __init__(self, role: str, text: str):
        self.role = role
        self.text = text

def _to_converse_msgs(history):
    return [{"role": m.role, "content": [{"text": m.text}]} for m in history]

# ========= Boto3 clients (region-pinned, role-based creds) =========
@lru_cache(maxsize=1)
def _brt():
    return boto3.client("bedrock-runtime", region_name=REGION)

@lru_cache(maxsize=1)
def _br_agent_rt():
    return boto3.client("bedrock-agent-runtime", region_name=REGION)

@lru_cache(maxsize=1)
def _br_agent():
    return boto3.client("bedrock-agent", region_name=REGION)

@lru_cache(maxsize=1)
def _br_ctrl():
    return boto3.client("bedrock", region_name=REGION)

@lru_cache(maxsize=1)
def _sts():
    return boto3.client("sts", region_name=REGION)

def _caller_identity_safe():
    try:
        i = _sts().get_caller_identity()
        return f"account={i.get('Account')} arn={i.get('Arn')}"
    except Exception as e:
        return f"(caller identity lookup failed: {type(e).__name__}: {e})"

# ========= Inference Profile resolver for Sonnet-4 =========
@lru_cache(maxsize=2)
def _resolve_inference_profile_arn(model_id: str) -> str:
    br = _br_ctrl()
    summaries = br.list_inference_profiles().get("inferenceProfileSummaries", [])
    # Prefer system-defined first
    ordered = sorted(summaries, key=lambda p: (p.get("type") != "SYSTEM_DEFINED", p.get("name", "")))
    for p in ordered:
        detail = br.get_inference_profile(inferenceProfileIdentifier=p["inferenceProfileArn"])
        for m in detail.get("models", []):
            if model_id in (m.get("modelArn") or ""):
                return detail["inferenceProfileArn"]
    raise RuntimeError(f"No inference profile contains '{model_id}' in {REGION}.")

# ========= Public APIs =========
def chat_with_model(message_history, new_text: str):
    """
    Plain model chat (Converse). Uses Inference Profile (required for Sonnet-4).
    """
    # update history (trim light)
    message_history.append(ChatMessage("user", new_text))
    if len(message_history) > MAX_MESSAGES:
        del message_history[0 : len(message_history) - MAX_MESSAGES]

    ip_arn = _resolve_inference_profile_arn(MODEL_ID)

    try:
        resp = _brt().converse(
            inferenceProfileArn=ip_arn,
            messages=_to_converse_msgs(message_history),
            inferenceConfig={"maxTokens": 2000, "temperature": 0, "topP": 0.9, "stopSequences": []},
        )
        out = resp["output"]["message"]["content"][0]["text"]
    except Exception as e:
        ident = _caller_identity_safe()
        out = f"Error during converse: {type(e).__name__}: {e}\n↳ identity: {ident}"

    message_history.append(ChatMessage("assistant", out))
    return out

def chat_with_kb(message_history, new_text: str):
    """
    Knowledge Base RAG via RetrieveAndGenerate.
    Uses Knowledge Base ID and Inference Profile ARN for generation.
    """
    # update history (trim light)
    message_history.append(ChatMessage("user", new_text))
    if len(message_history) > MAX_MESSAGES:
        del message_history[0 : len(message_history) - MAX_MESSAGES]

    ip_arn = _resolve_inference_profile_arn(MODEL_ID)

    prompt = (
        "You are a question answering agent.\n"
        "Use only the provided search results to answer the user's question.\n"
        "If results are insufficient, say you couldn't find an exact answer.\n"
        "Double-check user assertions against the results.\n"
        "Answer in the user's language.\n\n"
        "Search results (numbered):\n$search_results$\n\n"
        "$output_format_instructions$"
    )

    brt = _br_agent_rt()
    bra = _br_agent()

    try:
        resp = brt.retrieve_and_generate(
            input={"text": new_text},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": KB_ID,
                    "modelArn": ip_arn,  # Use Inference Profile ARN
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
        out = resp["output"]["text"]

    except brt.exceptions.ResourceNotFoundException:
        # Helpful diagnostics on KBs in this account/region
        try:
            lst = bra.list_knowledge_bases().get("knowledgeBaseSummaries", [])
            kb_list = "\n".join(
                f"- {kb['knowledgeBaseId']} | {kb.get('name','')} | {kb.get('status','')}"
                for kb in lst
            ) or "(none)"
        except Exception as e2:
            kb_list = f"(KB list failed: {type(e2).__name__}: {e2})"
        ident = _caller_identity_safe()
        out = (
            "⚠️ Knowledge Base not found.\n"
            f"- Provided KB_ID: {KB_ID}\n"
            f"- Region: {REGION}\n"
            f"- {ident}\n"
            f"- KBs in this account/region:\n{kb_list}\n"
            "→ Replace KB_ID with a valid one in this account/region."
        )

    except brt.exceptions.AccessDeniedException as e:
        out = (
            f"AccessDenied: {e}\n"
            "→ Ensure the runtime role has: bedrock-agent-runtime:RetrieveAndGenerate, "
            "bedrock-agent:GetKnowledgeBase, bedrock-agent:ListKnowledgeBases, and access to data sources (e.g., S3)."
        )

    except Exception as e:
        ident = _caller_identity_safe()
        out = f"Error during retrieve_and_generate: {type(e).__name__}: {e}\n↳ identity: {ident}"

    message_history.append(ChatMessage("assistant", out))
    return out

# ========= Optional: quick diagnostics (call manually if needed) =========
def debug_print_identity_and_kbs():
    ident = _caller_identity_safe()
    try:
        lst = _br_agent().list_knowledge_bases().get("knowledgeBaseSummaries", [])
    except Exception as e:
        lst = []
        print(f"[KB list error] {type(e).__name__}: {e}")

    print(f"[Identity] {ident}")
    print(f"[Region] {REGION}")
    try:
        ip_arn = _resolve_inference_profile_arn(MODEL_ID)
        print(f"[InferenceProfile for {MODEL_ID}] {ip_arn}")
    except Exception as e:
        print(f"[IP resolve error] {type(e).__name__}: {e}")

    print("[KBs in region]:")
    for kb in lst:
        print(f"  - {kb['knowledgeBaseId']} | {kb.get('name','')} | {kb.get('status','')}")
