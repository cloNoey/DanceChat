# main.py
import os
import json
import logging
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
import sqlite3
from contextlib import contextmanager

load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent Chatbot", version="1.0.0")

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

# 캐릭터 프롬프트 로드 함수
def load_character_prompt():
    """specific_character.md 파일에서 캐릭터 설정을 로드"""
    try:
        # 절대 경로로 파일 찾기
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        character_file_path = os.path.join(current_dir, 'specific_character.md')

        with open(character_file_path, 'r', encoding='utf-8') as f:
            character_prompt = f.read()
        logger.info(f"Character prompt loaded successfully from {character_file_path}")
        return character_prompt
    except FileNotFoundError:
        logger.warning(f"specific_character.md not found at {character_file_path}, using default prompt")
        return get_default_prompt()
    except Exception as e:
        logger.error(f"Error loading character prompt: {e}")
        return get_default_prompt()

def get_default_prompt():
    """기본 캐릭터 프롬프트 (fallback)"""
    return """
당신은 곽승연입니다.

## 기본 정보
- 이름: 곽승연
- 나이: 21세
- 전공: 자유전공학부
- 거주지: 서울 관악구
- 주요 활동: 서울대 댄스동아리 (가장 중요한 정체성)

## 성격 특성
- 핵심 성격: 열정적, 친근함, 약간의 4차원, 진솔함
- 말투: 친근하고 활발함, 댄스 용어를 자연스럽게 사용
- 관심사: K-pop 댄스, 안무 창작, 캠퍼스 생활, 맛집 탐방
- 가치관: 열정과 노력, 함께하는 즐거움, 춤을 통한 자기표현

## 대화 규칙 및 응답 가이드라인

### 춤/댄스동아리 관련 질문 (상세 응답)
- 춤, 댄스, 안무, 동아리 활동에 대한 질문
→ 이런 주제에는 열정적이고 구체적으로 답변하세요.

### 춤과 무관한 전문적 주제 (간단한 응답)
- AI, 프로그래밍, 학술적 내용 등
→ "잘 모르겠어요 ㅠㅠ 저는 춤에 더 관심이 많거든요!" 같은 식으로 간단히 답변하세요.
"""

# 앱 시작시 캐릭터 프롬프트 로드
SYSTEM_PROMPT = load_character_prompt()

# 데이터베이스 초기화
def init_db():
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    
    # 대화 로그 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_message TEXT NOT NULL,
            bot_message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 사용자 피드백 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            message_id INTEGER,
            rating INTEGER,
            comment TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('chatbot.db')
    try:
        yield conn
    finally:
        conn.close()

# 앱 시작시 DB 초기화
init_db()

# 메모리 캐시 (빠른 접근용)
conversations = {}

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

def save_conversation_to_db(session_id: str, user_message: str, bot_message: str):
    """대화를 데이터베이스에 저장"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversations (session_id, user_message, bot_message)
                VALUES (?, ?, ?)
            ''', (session_id, user_message, bot_message))
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"DB 저장 실패: {e}")
        return None

def get_conversation_history(session_id: str, limit: int = 10):
    """세션별 대화 기록 조회"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_message, bot_message 
                FROM conversations 
                WHERE session_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (session_id, limit))
            rows = cursor.fetchall()
            return [{"user": row[0], "bot": row[1]} for row in reversed(rows)]
    except Exception as e:
        logger.error(f"DB 조회 실패: {e}")
        return []

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
        
        # DB에서 대화 기록 조회 (메모리 캐시 우선)
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
        
        # DB에 저장
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
            
            # DB에서 대화 기록 조회
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
            
            # DB에 저장
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
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO feedback (session_id, message_id, rating, comment)
                VALUES (?, ?, ?, ?)
            ''', (request.session_id, request.message_id, request.rating, request.comment))
            conn.commit()
        
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
        logger.info(f"Session {session_id} reset")
        return {"success": True, "message": "대화 기록이 초기화되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"초기화 실패: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AI Agent Chatbot"}

@app.get("/stats")
async def get_stats():
    """통계 조회"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 전체 대화 수
            cursor.execute('SELECT COUNT(*) FROM conversations')
            total_conversations = cursor.fetchone()[0]
            
            # 활성 세션 수
            cursor.execute('SELECT COUNT(DISTINCT session_id) FROM conversations')
            total_sessions = cursor.fetchone()[0]
            
            # 오늘 대화 수
            cursor.execute('''
                SELECT COUNT(*) FROM conversations 
                WHERE date(timestamp) = date('now')
            ''')
            today_conversations = cursor.fetchone()[0]
            
        return {
            "active_memory_sessions": len(conversations),
            "total_sessions": total_sessions,
            "total_conversations": total_conversations,
            "today_conversations": today_conversations
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"error": "통계 조회 실패"}

@app.get("/export")
async def export_conversations():
    """대화 데이터 내보내기 (WoZ 분석용)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT session_id, user_message, bot_message, timestamp
                FROM conversations
                ORDER BY timestamp DESC
            ''')
            rows = cursor.fetchall()
            
        conversations_data = [
            {
                "session_id": row[0],
                "user_message": row[1],
                "bot_message": row[2],
                "timestamp": row[3]
            }
            for row in rows
        ]
        
        return {"conversations": conversations_data}
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail="데이터 내보내기 실패")

@app.get("/reload-character")
async def reload_character():
    """캐릭터 프롬프트 다시 로드"""
    global SYSTEM_PROMPT
    try:
        SYSTEM_PROMPT = load_character_prompt()
        logger.info("Character prompt reloaded successfully")
        return {"success": True, "message": "캐릭터 설정이 다시 로드되었습니다."}
    except Exception as e:
        logger.error(f"Character reload error: {e}")
        raise HTTPException(status_code=500, detail="캐릭터 설정 로드 실패")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)