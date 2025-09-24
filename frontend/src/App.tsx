import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  GlobalStyle,
  ChatContainer,
  ChatHeader,
  ExportButton,
  ChatMessages,
  Message,
  FeedbackButtons,
  FeedbackButton,
  ChatInput,
  Overlay,
  Sidebar,
  SidebarHeader,
  CloseButton,
  NewSessionButton,
  SessionList,
  SessionItem,
  SessionInfo,
  SessionName,
  SessionTime,
  DeleteSessionButton,
  MenuButton
} from './styles/ChatStyles';

interface Message {
  text: string;
  isUser: boolean;
  showFeedback?: boolean;
  feedbackGiven?: number;
}

interface Session {
  id: string;
  name: string;
  createdAt: string;
  messages: Message[];
}

const API_BASE_URL = import.meta.env.VITE_API_URL || window.location.origin;

function App() {
  // 세션 관리 초기화
  const initializeSessions = (): { sessions: Record<string, Session>, currentSessionId: string } => {
    const storedSessions = localStorage.getItem('chatSessions');
    let sessions: Record<string, Session> = storedSessions ? JSON.parse(storedSessions) : {};

    let currentSessionId = `session_${Date.now()}`;

    // 세션이 없으면 첫 세션 생성
    if (Object.keys(sessions).length === 0) {
      sessions[currentSessionId] = {
        id: currentSessionId,
        name: '세션 1',
        createdAt: new Date().toISOString(),
        messages: []
      };
      localStorage.setItem('chatSessions', JSON.stringify(sessions));
    } else {
      // 기존 세션 중 가장 최근 세션을 현재 세션으로 설정
      const sessionList = Object.values(sessions).sort((a, b) =>
        new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      );
      currentSessionId = sessionList[0].id;
    }

    return { sessions, currentSessionId };
  };

  const { sessions: initialSessions, currentSessionId: initialSessionId } = initializeSessions();

  const [messages, setMessages] = useState<Message[]>([{
    text: '안녕하세요!! 저는 서울대 댄스동아리에서 활동하고 있는 곽승연이라고 해요~ 🕺\n춤에 관심 있으시나요? 아니면 그냥 대화하러 오신 건가요? ㅎㅎ',
    isUser: false,
    showFeedback: true
  }]);
  const [inputMessage, setInputMessage] = useState('');
  const [sessions, setSessions] = useState<Record<string, Session>>(initialSessions);
  const [currentSessionId, setCurrentSessionId] = useState(initialSessionId);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);


  // 현재 세션의 메시지 복원
  useEffect(() => {
    const currentSession = sessions[currentSessionId];
    if (currentSession && currentSession.messages.length > 0) {
      setMessages([
        {
          text: '안녕하세요!! 저는 서울대 댄스동아리에서 활동하고 있는 곽승연이라고 해요~ 🕺\n춤에 관심 있으시나요? 아니면 그냥 대화하러 오신 건가요? ㅎㅎ',
          isUser: false,
          showFeedback: true
        },
        ...currentSession.messages
      ]);
    }
  }, [currentSessionId, sessions]);

  const handleSendMessage = async () => {
    const messageToSend = inputMessage.trim();
    if (!messageToSend) return;

    // 입력 즉시 클리어
    setInputMessage('');

    // 사용자 메시지 추가
    setMessages(prev => [...prev, { text: messageToSend, isUser: true }]);

    try {
      await handleStreamingMessage(messageToSend);
    } catch (error) {
      setMessages(prev => [...prev, { text: '네트워크 오류가 발생했어요 😭', isUser: false }]);
    }
  };


  const handleStreamingMessage = async (message: string) => {
    console.log('Starting streaming message:', message);

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          session_id: currentSessionId
        })
      });

      console.log('Response received, reading stream...');

      if (!response.body) {
        throw new Error('스트리밍 응답을 받을 수 없습니다');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullMessage = '';
      let botMessageIndex = -1;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              console.log('Received data:', data);

              if (data.type === 'start') {
                // 봇 메시지 시작 - 빈 메시지 추가 (타이핑 중 표시)
                setMessages(prev => {
                  botMessageIndex = prev.length;
                  return [...prev, {
                    text: '',
                    isUser: false,
                    showFeedback: false
                  }];
                });
                fullMessage = ''; // 초기화
              } else if (data.type === 'chunk' && data.content) {
                fullMessage += data.content;
                console.log('Updated fullMessage:', fullMessage);

                // 메시지 실시간 업데이트
                setMessages(prev => {
                  const newMessages = [...prev];
                  if (botMessageIndex >= 0 && newMessages[botMessageIndex]) {
                    newMessages[botMessageIndex] = {
                      ...newMessages[botMessageIndex],
                      text: fullMessage
                    };
                  }
                  return newMessages;
                });
              } else if (data.type === 'complete') {
                // 스트리밍 완료 - 피드백 버튼 활성화
                setMessages(prev => {
                  const newMessages = [...prev];
                  if (botMessageIndex >= 0 && newMessages[botMessageIndex]) {
                    newMessages[botMessageIndex] = {
                      ...newMessages[botMessageIndex],
                      showFeedback: true
                    };
                  }
                  return newMessages;
                });
                console.log('Streaming completed');
                return;
              }
            } catch (e) {
              console.error('JSON parse error:', e, 'Line:', line);
            }
          }
        }
      }
    } catch (error) {
      console.error('Streaming error:', error);
      setMessages(prev => [...prev, {
        text: '네트워크 오류가 발생했어요 😭',
        isUser: false,
        showFeedback: false
      }]);
    }
  };

  const handleFeedback = async (rating: number, messageIndex: number) => {
    try {
      await axios.post(`${API_BASE_URL}/feedback`, {
        session_id: currentSessionId,
        rating
      });

      setMessages(prev => {
        const newMessages = [...prev];
        if (newMessages[messageIndex]) {
          newMessages[messageIndex] = {
            ...newMessages[messageIndex],
            feedbackGiven: rating
          };
        }
        return newMessages;
      });
    } catch (error) {
      console.error('Feedback failed:', error);
    }
  };

  const handleExport = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/export`);
      const blob = new Blob([JSON.stringify(response.data, null, 2)], {
        type: 'application/json'
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `chatbot_conversations_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      alert('대화 데이터가 다운로드되었습니다!');
    } catch (error) {
      alert('데이터 내보내기 실패');
    }
  };

  // 세션 관리 함수들
  const openSidebar = () => {
    setIsSidebarOpen(true);
  };

  const closeSidebar = () => {
    setIsSidebarOpen(false);
  };

  const saveCurrentSession = () => {
    // 현재 메시지들을 현재 세션에 저장 (첫 번째 인사말 제외)
    const currentMessages = messages.slice(1);
    setSessions(prev => {
      const newSessions = {
        ...prev,
        [currentSessionId]: {
          ...prev[currentSessionId],
          messages: currentMessages
        }
      };
      localStorage.setItem('chatSessions', JSON.stringify(newSessions));
      return newSessions;
    });
  };

  const createNewSession = () => {
    // 현재 세션 저장
    saveCurrentSession();

    // 새 세션 생성
    const newSessionId = `session_${Date.now()}`;
    const newSession: Session = {
      id: newSessionId,
      name: `세션 ${Object.keys(sessions).length + 1}`,
      createdAt: new Date().toISOString(),
      messages: []
    };

    setSessions(prev => {
      const newSessions = { ...prev, [newSessionId]: newSession };
      localStorage.setItem('chatSessions', JSON.stringify(newSessions));
      return newSessions;
    });

    // 새 세션으로 전환
    setCurrentSessionId(newSessionId);

    // 메시지 초기화
    setMessages([{
      text: '안녕하세요!! 저는 서울대 댄스동아리에서 활동하고 있는 곽승연이라고 해요~ 🕺\n춤에 관심 있으시나요? 아니면 그냥 대화하러 오신 건가요? ㅎㅎ',
      isUser: false,
      showFeedback: true
    }]);

    closeSidebar();
  };

  const switchSession = (sessionId: string) => {
    if (sessionId === currentSessionId) return;

    // 현재 세션 저장
    saveCurrentSession();

    // 새 세션으로 전환
    setCurrentSessionId(sessionId);

    // 세션의 메시지 복원
    const session = sessions[sessionId];
    if (session && session.messages.length > 0) {
      setMessages([
        {
          text: '안녕하세요!! 저는 서울대 댄스동아리에서 활동하고 있는 곽승연이라고 해요~ 🕺\n춤에 관심 있으시나요? 아니면 그냥 대화하러 오신 건가요? ㅎㅎ',
          isUser: false,
          showFeedback: true
        },
        ...session.messages
      ]);
    } else {
      setMessages([{
        text: '안녕하세요!! 저는 서울대 댄스동아리에서 활동하고 있는 곽승연이라고 해요~ 🕺\n춤에 관심 있으시나요? 아니면 그냥 대화하러 오신 건가요? ㅎㅎ',
        isUser: false,
        showFeedback: true
      }]);
    }

    closeSidebar();
  };

  const deleteSession = async (sessionIdToDelete: string) => {
    if (Object.keys(sessions).length <= 1) {
      alert('최소 하나의 세션은 유지되어야 합니다.');
      return;
    }

    if (!confirm('이 세션을 삭제하시겠습니까?')) return;

    try {
      // 서버에서 세션 리셋 요청
      await axios.post(`${API_BASE_URL}/reset`, {
        session_id: sessionIdToDelete
      });
    } catch (error) {
      console.error('서버 세션 삭제 실패:', error);
    }

    // 클라이언트에서 세션 삭제
    setSessions(prev => {
      const newSessions = { ...prev };
      delete newSessions[sessionIdToDelete];
      localStorage.setItem('chatSessions', JSON.stringify(newSessions));

      // 현재 세션이 삭제된 경우 다른 세션으로 전환
      if (sessionIdToDelete === currentSessionId) {
        const remainingSessions = Object.keys(newSessions);
        if (remainingSessions.length > 0) {
          switchSession(remainingSessions[0]);
        }
      }

      return newSessions;
    });
  };

  return (
    <GlobalStyle>
      <Overlay isOpen={isSidebarOpen} onClick={closeSidebar} />

      <Sidebar isOpen={isSidebarOpen}>
        <SidebarHeader>
          <h2>세션 관리</h2>
          <CloseButton onClick={closeSidebar}>×</CloseButton>
        </SidebarHeader>
        <NewSessionButton onClick={createNewSession}>+ 새 세션</NewSessionButton>
        <SessionList>
          {Object.values(sessions)
            .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
            .map((session) => (
              <SessionItem key={session.id} isActive={session.id === currentSessionId}>
                <SessionInfo onClick={() => switchSession(session.id)}>
                  <SessionName>{session.name}</SessionName>
                  <SessionTime>{new Date(session.createdAt).toLocaleString()}</SessionTime>
                </SessionInfo>
                <DeleteSessionButton onClick={() => deleteSession(session.id)} title="세션 삭제">
                  🗑️
                </DeleteSessionButton>
              </SessionItem>
            ))}
        </SessionList>
      </Sidebar>

      <ChatContainer>
        <ChatHeader>
          <MenuButton onClick={openSidebar}>☰</MenuButton>
          <h1>무엇이든 물어보곽</h1>
          <p>서울대 댄스동아리</p>
          <ExportButton onClick={handleExport}>내보내기</ExportButton>
        </ChatHeader>

        <ChatMessages>
          {messages.map((message, index) => (
            <Message key={index} isUser={message.isUser}>
              <div style={{ whiteSpace: 'pre-wrap' }}>
                {message.text}
                {!message.isUser && !message.showFeedback && message.text === '' && (
                  <span style={{ opacity: 0.7 }}>타이핑 중...</span>
                )}
                {!message.isUser && message.text && !message.showFeedback && (
                  <span style={{
                    display: 'inline-block',
                    width: '2px',
                    height: '20px',
                    backgroundColor: '#667eea',
                    marginLeft: '2px',
                    animation: 'blink 1s infinite'
                  }}>|</span>
                )}
              </div>
              {!message.isUser && message.showFeedback && (
                <FeedbackButtons>
                  {[1, 2, 3].map((rating) => (
                    <FeedbackButton
                      key={rating}
                      isSelected={message.feedbackGiven === rating}
                      onClick={() => handleFeedback(rating, index)}
                    >
                      {rating === 1 ? '👍' : rating === 2 ? '😐' : '👎'}
                    </FeedbackButton>
                  ))}
                </FeedbackButtons>
              )}
            </Message>
          ))}
          <div ref={messagesEndRef} />
        </ChatMessages>

        <ChatInput>
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                e.stopPropagation();
                handleSendMessage();
              }
            }}
            placeholder="메시지를 입력하세요..."
            maxLength={500}
          />
          <button onClick={handleSendMessage}>전송</button>
        </ChatInput>
      </ChatContainer>
    </GlobalStyle>
  );
}

export default App;