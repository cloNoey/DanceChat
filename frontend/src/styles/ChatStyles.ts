import styled from '@emotion/styled';

export const ChatContainer = styled.div`
  width: 90%;
  max-width: 400px;
  height: 90vh;
  max-height: 600px;
  background: white;
  border-radius: 20px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
`;

export const ChatHeader = styled.div`
  background: #667eea;
  color: white;
  padding: 20px;
  text-align: center;
  position: relative;

  h1 {
    font-size: 18px;
    margin-bottom: 5px;
  }

  p {
    font-size: 12px;
    opacity: 0.8;
  }
`;

export const ExportButton = styled.button`
  position: absolute;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255,255,255,0.2);
  border: none;
  color: white;
  padding: 8px 12px;
  border-radius: 15px;
  cursor: pointer;
  font-size: 12px;
`;

export const ChatMessages = styled.div`
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 15px;
`;

export const Message = styled.div<{ isUser?: boolean }>`
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 18px;
  word-wrap: break-word;
  position: relative;
  background: ${props => props.isUser ? '#667eea' : '#f1f3f5'};
  color: ${props => props.isUser ? 'white' : '#333'};
  align-self: ${props => props.isUser ? 'flex-end' : 'flex-start'};
`;

export const FeedbackButtons = styled.div`
  display: flex;
  gap: 5px;
  margin-top: 8px;
`;

export const FeedbackButton = styled.button<{ isSelected?: boolean }>`
  background: ${props => props.isSelected ? '#667eea' : '#ddd'};
  color: ${props => props.isSelected ? 'white' : 'inherit'};
  border: none;
  padding: 4px 8px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 12px;
`;

export const ChatInput = styled.div`
  padding: 20px;
  border-top: 1px solid #eee;
  display: flex;
  gap: 10px;

  input {
    flex: 1;
    padding: 12px 16px;
    border: 1px solid #ddd;
    border-radius: 20px;
    outline: none;
    font-size: 14px;
  }

  button {
    padding: 12px 20px;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 20px;
    cursor: pointer;
    font-size: 14px;

    &:hover {
      background: #5a6fd8;
    }
  }
`;

export const Stats = styled.div`
  position: absolute;
  bottom: 10px;
  left: 10px;
  color: white;
  font-size: 10px;
  opacity: 0.7;
`;

export const GlobalStyle = styled.div`
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
  }
`;

export const Overlay = styled.div<{ isOpen: boolean }>`
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0,0,0,0.5);
  display: ${props => props.isOpen ? 'block' : 'none'};
  z-index: 999;
`;

export const Sidebar = styled.div<{ isOpen: boolean }>`
  position: fixed;
  left: ${props => props.isOpen ? '0' : '-300px'};
  top: 0;
  width: 300px;
  height: 100vh;
  background: white;
  box-shadow: 2px 0 10px rgba(0,0,0,0.1);
  transition: left 0.3s ease;
  z-index: 1000;
  padding: 20px;
  overflow-y: auto;
`;

export const SidebarHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;

  h2 {
    margin: 0;
    color: #333;
    font-size: 16px;
  }
`;

export const CloseButton = styled.button`
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #666;

  &:hover {
    color: #333;
  }
`;

export const NewSessionButton = styled.button`
  width: 100%;
  padding: 10px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 15px;
  font-size: 14px;

  &:hover {
    background: #5a6fd8;
  }
`;

export const SessionList = styled.ul`
  list-style: none;
  padding: 0;
`;

export const SessionItem = styled.li<{ isActive: boolean }>`
  padding: 10px;
  margin-bottom: 10px;
  background: ${props => props.isActive ? '#667eea' : '#f8f9fa'};
  color: ${props => props.isActive ? 'white' : 'inherit'};
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;

  &:hover:not(.active) {
    background: ${props => props.isActive ? '#667eea' : '#e9ecef'};
  }
`;

export const SessionInfo = styled.div`
  flex: 1;
`;

export const SessionName = styled.div`
  font-weight: bold;
  font-size: 12px;
`;

export const SessionTime = styled.div`
  font-size: 10px;
  opacity: 0.7;
`;

export const DeleteSessionButton = styled.button`
  background: none;
  border: none;
  color: red;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  font-size: 16px;

  &:hover {
    background: rgba(255,0,0,0.1);
  }
`;

export const MenuButton = styled.button`
  position: absolute;
  left: 15px;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255,255,255,0.2);
  border: none;
  color: white;
  padding: 8px 10px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 14px;

  &:hover {
    background: rgba(255,255,255,0.3);
  }
`;
