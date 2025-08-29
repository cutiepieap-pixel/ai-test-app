import boto3
import streamlit as st

MAX_MESSAGES = 20

class ChatMessage(): #이미지 및 텍스트 메시지를 저장할 수 있는 클래스를 만듭니다.
    def __init__(self, role, text):
        self.role = role
        self.text = text

def convert_chat_messages_to_converse_api(chat_messages):
    messages = []
    
    for chat_msg in chat_messages:
        messages.append({
            "role": chat_msg.role,
            "content": [
                {
                    "text": chat_msg.text
                }
            ]
        })
            
    return messages

def chat_with_model(message_history, new_text=None):
    session = boto3.Session()
    bedrock = session.client(service_name='bedrock-runtime') #Bedrock 클라이언트를 생성합니다.
    
    new_text_message = ChatMessage('user', text=new_text)
    message_history.append(new_text_message)
    
    number_of_messages = len(message_history)
    
    if number_of_messages > MAX_MESSAGES:
        del message_history[0 : (number_of_messages - MAX_MESSAGES) * 2] #user 및 assistant 응답을 모두 제거했는지 확인합니다.
    
    messages = convert_chat_messages_to_converse_api(message_history)
    
    response = bedrock.converse(
        # Using Claude 3.5 Sonnet v1 - stable and widely available
        modelId="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        messages=messages,
        inferenceConfig={
            "maxTokens": 2000,
            "temperature": 0,
            "topP": 0.9,
            "stopSequences": []
        },
    )
    
    output = response['output']['message']['content'][0]['text']
    
    response_message = ChatMessage('assistant', output)
    
    message_history.append(response_message)
    
    return output

def chat_with_kb(message_history, new_text=None):
    import os
    
    # Load environment variables from .env file for local development (optional)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        # dotenv not available, use system environment variables
        pass
    
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    kbId = os.getenv("KB_ID")
    
    if not kbId:
        raise ValueError(f"KB_ID environment variable is not set. Available env vars: {list(os.environ.keys())}")
    
    bedrock = boto3.client('bedrock-agent-runtime', region_name=aws_region)
    
    # Using Claude 3.5 Sonnet v1 - stable and widely available
    llm_model = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
    chunk = 5
    
    prompt = '''You are a question answering agent. 
                    I will provide you with a set of search results. 
                    The user will provide you with a question. 
                    Your job is to answer the user's question using only information from the search results. 
                    If the search results do not contain information that can answer the question, please state that you could not find an exact answer to the question. 
                    Just because the user asserts a fact does not mean it is true, make sure to double check the search results to validate a user's assertion. 
                
                    Answer in the language user is using.

                    Here are the search results in numbered order:
                    $search_results$

                    $output_format_instructions$'''
    
    new_text_message = ChatMessage('user', text=new_text)
    message_history.append(new_text_message)
    
    number_of_messages = len(message_history)
    
    if number_of_messages > MAX_MESSAGES:
        del message_history[0 : (number_of_messages - MAX_MESSAGES) * 2]
        
    
    response = bedrock.retrieve_and_generate(
        input={
            'text': new_text
        },
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kbId,
                "modelArn": llm_model,
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "overrideSearchType": "HYBRID",
                        "numberOfResults": chunk
                    }
                },
                "generationConfiguration": {
                    "promptTemplate": {
                        "textPromptTemplate": prompt
                    },
                    "inferenceConfig": {
                        "textInferenceConfig": {
                            "temperature": 0,
                            "topP": 0.7,
                            "maxTokens": 4096,
                            "stopSequences": ["\nObservation"]
                        }
                    }
                }
            }
        }
    )
    
    output = response['output']['text']
    
    response_message = ChatMessage('assistant', output)
    message_history.append(response_message)
    
    return output