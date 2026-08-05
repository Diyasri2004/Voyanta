"use client";

import { useState } from "react";
import { MessageSquare, X, Send } from "lucide-react";

import { useCurrency } from "@/context/CurrencyContext";

export default function Voya({ trip }: { trip: any }) {
  const { currency } = useCurrency();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: "assistant", content: "I am Voya, your AI Travel Concierge. How can I modify your agenda?" }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setInput("");
    setIsLoading(true);

    try {
      // In a real implementation this would hit our Next.js API route using @google/genai
      // For now, we simulate a response
      setTimeout(() => {
        setMessages(prev => [...prev, { 
          role: "assistant", 
          content: `Checking ${trip?.destination || "your destination"}... I see you are using ${currency}. I recommend updating your packing list.`
        }]);
        setIsLoading(false);
      }, 1000);
    } catch (e) {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Floating Button */}
      <button 
        onClick={() => setIsOpen(true)}
        className={`absolute bottom-6 right-6 h-14 w-14 rounded-full bg-[#00f0ff] flex items-center justify-center text-black shadow-[0_0_20px_rgba(0,240,255,0.6)] hover:scale-110 transition-transform z-50 ${isOpen ? 'scale-0 opacity-0' : 'scale-100 opacity-100'}`}
      >
        <MessageSquare className="h-6 w-6" />
      </button>

      {/* Chat Drawer */}
      <div className={`absolute bottom-0 right-0 w-80 sm:w-96 h-[500px] max-h-screen bg-[#03050a]/95 backdrop-blur-xl border-l border-t border-[#00f0ff]/30 shadow-[-10px_-10px_30px_rgba(0,0,0,0.8)] z-50 transition-transform duration-300 flex flex-col ${isOpen ? 'translate-y-0' : 'translate-y-full'}`}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#00f0ff]/20">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[#39ff14] animate-pulse" />
            <h3 className="font-syne font-bold text-[#00f0ff]">Voya - AI Travel Concierge</h3>
          </div>
          <button onClick={() => setIsOpen(false)} className="text-white/50 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3 hide-scrollbar">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-xl p-3 text-sm ${
                m.role === "user" 
                  ? "bg-[#ff007f] text-white rounded-br-sm" 
                  : "bg-white/10 text-[#00f0ff] border border-[#00f0ff]/20 rounded-bl-sm font-mono"
              }`}>
                {m.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white/10 border border-[#00f0ff]/20 rounded-xl p-3 text-sm flex gap-1">
                <div className="w-2 h-2 bg-[#00f0ff] rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-[#00f0ff] rounded-full animate-bounce [animation-delay:0.2s]" />
                <div className="w-2 h-2 bg-[#00f0ff] rounded-full animate-bounce [animation-delay:0.4s]" />
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <form onSubmit={sendMessage} className="p-4 border-t border-[#00f0ff]/20 bg-black/50">
          <div className="flex items-center bg-white/5 border border-white/10 rounded-full pr-2 focus-within:border-[#00f0ff]/50 transition-colors">
            <input 
              type="text" 
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Command Voya..."
              className="flex-1 bg-transparent px-4 py-3 text-sm outline-none text-white placeholder-white/40"
            />
            <button type="submit" disabled={!input.trim()} className="bg-[#00f0ff] text-black p-2 rounded-full hover:bg-white disabled:opacity-50 transition-colors">
              <Send className="h-4 w-4" />
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
