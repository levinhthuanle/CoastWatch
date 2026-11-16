import ChatPanel from '../components/Chat/ChatPanel'
import Sidebar from '../components/Layout/Sidebar'

export default function ChatPage() {
  return (
    <div className="flex h-screen bg-slate-900 overflow-hidden">
      <Sidebar />
      <div className="flex-1 overflow-hidden">
        <ChatPanel />
      </div>
    </div>
  )
}
