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

  const SUGGESTIONS = [
    "🍣 Top local food spots?",
    "☔ Rainy day backup plan?",
    "🚌 Local transit tips?"
  ];

  const sendMessage = async (e?: React.FormEvent, presetMessage?: string) => {
    if (e) e.preventDefault();
    const userMsg = presetMessage || input.trim();
    if (!userMsg || isLoading) return;

    const newMessages = [...messages, { role: "user", content: userMsg }];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages,
          context: {
            destination: trip?.destination,
            budget: trip?.budget,
            currency: currency,
            itinerary: trip?.itinerary
          }
        })
      });
      const data = await response.json();
      
      if (data.reply) {
        setMessages(prev => [...prev, { role: "assistant", content: data.reply }]);
      } else {
        setMessages(prev => [...prev, { role: "assistant", content: "I'm having trouble connecting to my neural network. Try again later!" }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", content: "My connection dropped. Please try again." }]);
    } finally {
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
        <span className="text-2xl drop-shadow-[0_0_8px_rgba(255,255,255,0.8)] animate-bounce" style={{ animationDuration: '2s' }}>🤖</span>
      </button>

      {/* Chat Drawer */}
      <div className={`absolute bottom-0 right-0 w-80 sm:w-96 h-[500px] max-h-screen bg-[#03050a]/95 backdrop-blur-xl border-l border-t border-[#00f0ff]/30 shadow-[-10px_-10px_30px_rgba(0,0,0,0.8)] z-50 transition-transform duration-300 flex flex-col ${isOpen ? 'translate-y-0' : 'translate-y-full'}`}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#00f0ff]/20 bg-gradient-to-r from-[#00f0ff]/10 to-transparent">
          <div className="flex items-center gap-3">
            <div className="relative group cursor-help">
              <span className="text-2xl drop-shadow-[0_0_8px_rgba(0,240,255,0.8)] inline-block transition-transform group-hover:scale-125 group-hover:-rotate-12 duration-300">🤖</span>
            </div>
            <div>
              <h3 className="font-syne font-bold text-[#00f0ff] flex items-center gap-2">
                Voya 
                <span className="inline-block transition-transform hover:scale-125 hover:rotate-12 duration-300 cursor-pointer drop-shadow-[0_0_5px_rgba(255,0,127,0.8)]">✨</span>
              </h3>
              <p className="text-[10px] text-[#00f0ff]/70 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#39ff14] animate-pulse inline-block" /> Online
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xl transition-transform hover:scale-125 hover:-translate-y-1 duration-300 cursor-pointer drop-shadow-[0_0_5px_rgba(57,255,20,0.8)]">✈️</span>
            <span className="text-xl transition-transform hover:scale-125 hover:-translate-y-1 duration-300 cursor-pointer drop-shadow-[0_0_5px_rgba(255,0,127,0.8)]">🍣</span>
            <button onClick={() => setIsOpen(false)} className="text-white/50 hover:text-white ml-2">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3 hide-scrollbar">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-xl p-3 text-sm ${
                m.role === "user" 
                  ? "bg-gradient-to-br from-[#ff007f] to-[#ff007f]/80 text-white rounded-br-sm shadow-[0_0_15px_rgba(255,0,127,0.3)]" 
                  : "bg-white/5 text-[#e2e8f0] border border-[#00f0ff]/20 rounded-bl-sm font-plus-jakarta shadow-[0_0_15px_rgba(0,240,255,0.05)]"
              }`}>
                {m.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white/5 border border-[#00f0ff]/20 rounded-xl p-3 text-sm flex gap-1">
                <div className="w-2 h-2 bg-[#00f0ff] rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-[#00f0ff] rounded-full animate-bounce [animation-delay:0.2s]" />
                <div className="w-2 h-2 bg-[#00f0ff] rounded-full animate-bounce [animation-delay:0.4s]" />
              </div>
            </div>
          )}
        </div>

        {/* Quick Prompts */}
        <div className="px-4 pb-2 flex gap-2 overflow-x-auto hide-scrollbar">
          {SUGGESTIONS.map((sug, idx) => (
            <button
              key={idx}
              onClick={() => sendMessage(undefined, sug)}
              className="whitespace-nowrap text-[10px] bg-[#00f0ff]/10 text-[#00f0ff] border border-[#00f0ff]/30 px-3 py-1.5 rounded-full hover:bg-[#00f0ff]/20 transition-colors"
            >
              {sug}
            </button>
          ))}
        </div>

        {/* Input */}
        <form onSubmit={(e) => sendMessage(e)} className="p-4 border-t border-[#00f0ff]/20 bg-black/50">
          <div className="flex items-center bg-white/5 border border-white/10 rounded-full pr-2 focus-within:border-[#00f0ff]/50 transition-colors">
            <input 
              type="text" 
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask Voya..."
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
