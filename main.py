import os
import json
import logging
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

# 로깅 설정 (Vercel 환경에 최적화)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent Chatbot", version="1.0.1")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini 설정
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

# 캐릭터 프롬프트 (파일 읽기 대신 환경변수나 직접 정의)
def get_character_prompt():
    """캐릭터 프롬프트 반환"""
    # Vercel에서는 파일 시스템 접근이 제한적이므로 환경변수나 직접 정의 사용
    character_prompt = os.getenv('CHARACTER_PROMPT', '''
당신은 승연이라는 이름의 AI 어시스턴트입니다.
친근하고 도움이 되는 대화를 나누세요.
사용자의 질문에 정확하고 유용한 답변을 제공하세요.
''')
    return character_prompt

# 캐릭터 프롬프트 설정
SYSTEM_PROMPT = get_character_prompt()

# 전역 메모리 저장소 (Vercel의 serverless 환경에서는 휘발성)
conversations_store = {}
feedback_store = []
conversations = {}

def save_to_memory_store(session_id: str, user_message: str, bot_message: str):
    if session_id not in conversations_store:
        conversations_store[session_id] = []
    conversations_store[session_id].append({
        'user_message': user_message,
        'bot_message': bot_message,
        'timestamp': datetime.now().isoformat()
    })
    return len(conversations_store[session_id])

def save_conversation_to_db(session_id: str, user_message: str, bot_message: str):
    """대화를 메모리에 저장"""
    try:
        return save_to_memory_store(session_id, user_message, bot_message)
    except Exception as e:
        logger.error(f"메모리 저장 실패: {e}")
        return None

def get_conversation_history(session_id: str, limit: int = 10):
    """세션별 대화 기록 조회"""
    try:
        if session_id not in conversations_store:
            return []
        conversations = conversations_store[session_id][-limit:]
        return [{"user": conv["user_message"], "bot": conv["bot_message"]} 
                for conv in conversations]
    except Exception as e:
        logger.error(f"대화 기록 조회 실패: {e}")
        return []

# Request/Response 모델
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None

class FeedbackRequest(BaseModel):
    session_id: str
    message_id: Optional[int] = None
    rating: int  # 1-5
    comment: Optional[str] = None

@app.get("/")
async def root():
    """루트 엔드포인트 - Vercel 헬스체크용"""
    return {"message": "AI Agent Chatbot is running on Vercel", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AI Agent Chatbot", "platform": "Vercel"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        user_message = request.message.strip()
        session_id = request.session_id or "default"
        
        # 입력 검증
        if not user_message:
            raise HTTPException(status_code=400, detail="메시지가 비어있습니다.")
        if len(user_message) > 500:
            raise HTTPException(status_code=400, detail="메시지가 너무 깁니다.")
        
        logger.info(f"Session {session_id}: User message received")
        
        # 대화 기록 조회
        if session_id in conversations:
            recent_conversations = conversations[session_id][-10:]
        else:
            recent_conversations = get_conversation_history(session_id, 10)
            conversations[session_id] = recent_conversations
        
        # 컨텍스트 구성
        context = SYSTEM_PROMPT + "\n\n이전 대화:\n"
        for conv in recent_conversations:
            context += f"사용자: {conv['user']}\n승연: {conv['bot']}\n"
        context += f"\n현재 사용자 메시지: {user_message}\n승연:"
        
        # Gemini API 호출
        response = model.generate_content(context)
        bot_message = response.text
        
        # 메모리 캐시 업데이트
        if session_id not in conversations:
            conversations[session_id] = []
        conversations[session_id].append({
            'user': user_message,
            'bot': bot_message
        })
        
        # 저장
        message_id = save_conversation_to_db(session_id, user_message, bot_message)
        
        logger.info(f"Session {session_id}: Response generated successfully")
        
        return ChatResponse(success=True, message=bot_message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(success=False, error=f"서버 오류: {str(e)}")

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """스트리밍 채팅 엔드포인트"""
    from fastapi.responses import StreamingResponse
    import json
    
    async def generate_stream():
        try:
            user_message = request.message.strip()
            session_id = request.session_id or "default"
            
            # 입력 검증
            if not user_message:
                yield f"data: {json.dumps({'error': '메시지가 비어있습니다.'})}\n\n"
                return
            
            if len(user_message) > 500:
                yield f"data: {json.dumps({'error': '메시지가 너무 깁니다.'})}\n\n"
                return
            
            logger.info(f"Session {session_id}: Streaming chat started")
            
            # 대화 기록 조회
            if session_id in conversations:
                recent_conversations = conversations[session_id][-10:]
            else:
                recent_conversations = get_conversation_history(session_id, 10)
                conversations[session_id] = recent_conversations
            
            # 컨텍스트 구성
            context = SYSTEM_PROMPT + "\n\n이전 대화:\n"
            for conv in recent_conversations:
                context += f"사용자: {conv['user']}\n승연: {conv['bot']}\n"
            context += f"\n현재 사용자 메시지: {user_message}\n승연:"
            
            # 스트리밍 시작 신호
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            
            # Gemini 스트리밍 호출
            response = model.generate_content(context, stream=True)
            
            full_message = ""
            for chunk in response:
                if chunk.text:
                    full_message += chunk.text
                    # 각 청크를 클라이언트에 전송
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk.text})}\n\n"
            
            # 스트리밍 완료 신호
            yield f"data: {json.dumps({'type': 'complete', 'full_message': full_message})}\n\n"
            
            # 메모리 캐시 업데이트
            if session_id not in conversations:
                conversations[session_id] = []
            conversations[session_id].append({
                'user': user_message,
                'bot': full_message
            })
            
            # 저장
            save_conversation_to_db(session_id, user_message, full_message)
            
            logger.info(f"Session {session_id}: Streaming completed")
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """사용자 피드백 수집"""
    try:
        feedback_store.append({
            "session_id": request.session_id,
            "message_id": request.message_id,
            "rating": request.rating,
            "comment": request.comment,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Feedback received: {request.rating}/5 from {request.session_id}")
        return {"success": True, "message": "피드백이 저장되었습니다."}
    except Exception as e:
        logger.error(f"Feedback save error: {e}")
        raise HTTPException(status_code=500, detail="피드백 저장 실패")

@app.post("/reset")
async def reset_conversation(request: dict):
    """대화 초기화"""
    try:
        session_id = request.get('session_id', 'default')
        if session_id in conversations:
            del conversations[session_id]
        if session_id in conversations_store:
            del conversations_store[session_id]
        logger.info(f"Session {session_id} reset")
        return {"success": True, "message": "대화 기록이 초기화되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"초기화 실패: {str(e)}")

@app.get("/stats")
async def get_stats():
    """통계 조회"""
    try:
        total_conversations = sum(len(convs) for convs in conversations_store.values())
        total_sessions = len(conversations_store)
        
        # 오늘 대화 수 계산
        today = datetime.now().date()
        today_conversations = sum(
            1 for convs in conversations_store.values()
            for conv in convs
            if datetime.fromisoformat(conv["timestamp"]).date() == today
        )
        
        return {
            "platform": "Vercel",
            "active_memory_sessions": len(conversations),
            "total_sessions": total_sessions,
            "total_conversations": total_conversations,
            "today_conversations": today_conversations,
            "note": "Data is volatile in serverless environment"
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"error": "통계 조회 실패"}

@app.get("/export")
async def export_conversations():
    """대화 데이터 내보내기"""
    try:
        conversations_data = []
        for session_id, convs in conversations_store.items():
            for conv in convs:
                conversations_data.append({
                    "session_id": session_id,
                    "user_message": conv["user_message"],
                    "bot_message": conv["bot_message"],
                    "timestamp": conv["timestamp"]
                })
        
        return {
            "conversations": conversations_data,
            "note": "Data is volatile in Vercel serverless environment"
        }
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail="데이터 내보내기 실패")

@app.get("/reload-character")
async def reload_character():
    """캐릭터 프롬프트 다시 로드"""
    global SYSTEM_PROMPT
    try:
        SYSTEM_PROMPT = get_character_prompt()
        logger.info("Character prompt reloaded successfully")
        return {"success": True, "message": "캐릭터 설정이 다시 로드되었습니다."}
    except Exception as e:
        logger.error(f"Character reload error: {e}")
        raise HTTPException(status_code=500, detail="캐릭터 설정 로드 실패")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)