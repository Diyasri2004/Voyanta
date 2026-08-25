"use client";

import { useState, useEffect } from "react";
import { MessageSquare, X, Send } from "lucide-react";

import { useCurrency } from "@/context/CurrencyContext";

export default function Voya({ trip }: { trip: any }) {
  const { currency } = useCurrency();
  const getTimeGreeting = () => {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 12) return 'Good morning';
    if (hour >= 12 && hour < 17) return 'Good afternoon';
    if (hour >= 17 && hour < 22) return 'Good evening';
    return 'Good night';
  };

  const getExactOpeningMessage = () => {
    const timeGreeting = getTimeGreeting();
    return `${timeGreeting}! Welcome to Voyanta 🙏\nI'm Voya. Whether you need inspiration for your next getaway or help with an ongoing booking, I've got you covered. What destination is on your mind today?`;
  };

  const LANGUAGE_CONFIRMATIONS: Record<string, string> = {
    en: "You're all set in English! Feel free to ask about any destination, itinerary, or booking.",
    hi: "हिन्दी चुनने के लिए धन्यवाद! 🙏\n(You can type in हिन्दी or English letters / Hinglish).",
    ta: "தமிழைத் தேர்ந்தெடுத்ததற்கு நன்றி! 🙏\n(You can type in தமிழ் or English letters / Tanglish).",
    te: "తెలుగు ఎంచుకున్నందుకు ధన్యవాదాలు! 🙏\n(You can type in తెలుగు or English letters / Teluglish).",
    kn: "ಕನ್ನಡವನ್ನು ಆಯ್ಕೆ ಮಾಡಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು! 🙏\n(You can type in ಕನ್ನಡ or English letters / Kanglish).",
    ml: "മലയാളം തിരഞ്ഞെടുത്തതിന് നന്ദി! 🙏\n(You can type in മലയാളം or English letters / Manglish).",
    bn: "বাংলা বেছে নেওয়ার জন্য धन्यवाद! 🙏\n(You can type in বাংলা or English letters / Banglish).",
    ar: "شكراً لاختيارك اللغة العربية! 🌟\n(You can type in العربية or Latin letters / Arabizi).",
    es: "¡Gracias por elegir español! 🌟\n(Puedes escribir en español o inglés).",
    fr: "Merci d'avoir choisi le français ! 🌟\n(Vous pouvez écrire en français ou en anglais).",
    de: "Vielen Dank, dass Sie Deutsch gewählt haben! 🌟\n(Sie können auf Deutsch oder Englisch schreiben).",
    zh: "感谢您选择中文！🌟\n(您可以使用中文汉字或拼音/Pinyin进行输入)。",
    ru: "Спасибо, что выбрали русский язык! 🌟\n(Вы можете писать на русском или латиницей/транслитом)."
  };

  const [activeLang, setActiveLang] = useState("en");

  const selectLanguage = (code: string) => {
    setActiveLang(code);
    const confirmation = LANGUAGE_CONFIRMATIONS[code] || LANGUAGE_CONFIRMATIONS.en;
    setMessages(prev => [...prev, { role: "assistant", content: confirmation, text: confirmation }]);
  };

  interface ChatItem {
    role: string;
    content: string;
    text?: string;
    action?: any;
  }

  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatItem[]>([
    {
      role: 'assistant',
      content: `${getTimeGreeting()}! Welcome to Voyanta 🙏`,
      action: null
    },
    {
      role: 'assistant',
      content: trip?.destination
        ? `I'm Voya. Ready to explore ${trip.destination}! Whether you need inspiration or help with an ongoing booking, I've got you covered. What destination or plan is on your mind today?`
        : "I'm Voya. Whether you need inspiration for your next getaway or help with an ongoing booking, I've got you covered. What destination is on your mind today?",
      action: null
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (messages.length <= 2 && messages.every(m => m.role === 'assistant')) {
      setMessages([
        {
          role: 'assistant',
          content: `${getTimeGreeting()}! Welcome to Voyanta 🙏`,
          action: null
        },
        {
          role: 'assistant',
          content: trip?.destination 
            ? `I'm Voya. Ready to explore ${trip.destination}! Whether you need inspiration or help with an ongoing booking, I've got you covered. What destination or plan is on your mind today?`
            : "I'm Voya. Whether you need inspiration for your next getaway or help with an ongoing booking, I've got you covered. What destination is on your mind today?",
          action: null
        }
      ]);
    }
  }, [trip?.destination]);

  useEffect(() => {
    const handlePopState = () => {
      if (isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [isOpen]);

  const openDrawer = () => {
    if (typeof window !== "undefined") {
      window.history.pushState({ step: "dashboard", modal: "voya" }, "");
    }
    setIsOpen(true);
  };

  const SUGGESTIONS = [
    "✨ Swap an activity for a hidden gem",
    "🍱 Top local food spots & budget",
    "🚗 Local transit & navigation tips",
    "☔ Rainy day backup plan",
  ];

  const sendMessage = async (e?: React.FormEvent, presetMessage?: string) => {
    if (e) e.preventDefault();
    const userMsg = presetMessage || input.trim();
    if (!userMsg || isLoading) return;

    const newMessages = [...messages, { role: "user", content: userMsg, text: userMsg }];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg,
          destination: trip?.destination || '',
          currency: currency || 'USD',
          user_time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          user_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
          history: newMessages.map(m => ({ role: m.role, content: m.content || m.text })),
          active_itinerary: trip?.itinerary || []
        })
      });

      if (!response.ok) {
        console.error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const outputText = data.reply || data.response || data.message || "Here is what I found for you:";

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: outputText,
          text: outputText,
          action: data.action || null
        }
      ]);
    } catch (err) {
      console.error("Voya Chat Fetch Error:", err);
      setMessages(prev => [...prev, { role: "assistant", content: "Connection hiccup. Please try again.", text: "Connection hiccup. Please try again." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-[9999] pointer-events-auto flex flex-col items-end">
      {/* Chat Drawer */}
      <div className={`absolute bottom-full right-0 mb-4 w-80 sm:w-96 h-[500px] max-h-[80vh] bg-[#03050a]/95 backdrop-blur-xl border border-[#ff007f]/40 rounded-2xl shadow-[0_0_30px_rgba(255,0,127,0.2)] z-50 transition-all duration-300 flex flex-col origin-bottom-right ${isOpen ? 'scale-100 opacity-100' : 'scale-90 opacity-0 pointer-events-none'}`}>
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
            <select
              value={activeLang}
              onChange={(e) => selectLanguage(e.target.value)}
              className="bg-black/60 text-[#00f0ff] border border-[#00f0ff]/30 text-[10px] rounded-lg px-1.5 py-1 focus:outline-none cursor-pointer"
            >
              <option value="en">🌐 EN</option>
              <option value="hi">🇮🇳 HI (Hinglish)</option>
              <option value="ta">🇮🇳 TA (Tanglish)</option>
              <option value="te">🇮🇳 TE (Teluglish)</option>
              <option value="kn">🇮🇳 KN (Kanglish)</option>
              <option value="ml">🇮🇳 ML (Manglish)</option>
              <option value="bn">🇮🇳 BN (Banglish)</option>
              <option value="ar">🌍 AR (Arabizi)</option>
              <option value="es">🇪🇸 ES</option>
              <option value="fr">🇫🇷 FR</option>
              <option value="de">🇩🇪 DE</option>
              <option value="zh">🇨🇳 ZH (Pinyin)</option>
              <option value="ru">🇷🇺 RU (Translit)</option>
            </select>
            <button onClick={() => setIsOpen(false)} className="text-white/50 hover:text-white ml-1">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3 hide-scrollbar">
          {messages.map((m: any, i: number) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-xl p-3 text-sm ${
                m.role === "user" 
                  ? "bg-gradient-to-br from-[#ff007f] to-[#ff007f]/80 text-white rounded-br-sm shadow-[0_0_15px_rgba(255,0,127,0.3)]" 
                  : "bg-white/5 text-[#e2e8f0] border border-[#00f0ff]/20 rounded-bl-sm font-plus-jakarta shadow-[0_0_15px_rgba(0,240,255,0.05)]"
              }`}>
                <p className="whitespace-pre-wrap">{m.content || m.text}</p>
                {/* Action Badges */}
                {m.action?.booking_platforms && (
                  <div className="mt-2.5 pt-2 border-t border-white/10 space-y-1">
                    <div className="text-[11px] font-semibold text-[#ff007f]">🏨 Stays:</div>
                    <div className="grid grid-cols-2 gap-1 text-[10px]">
                      {Object.entries(m.action.booking_platforms).map(([p, u]: any) => (
                        <a key={p} href={u} target="_blank" rel="noreferrer" className="capitalize text-[#00f0ff] underline truncate">{p.replace('_', ' ')}</a>
                      ))}
                    </div>
                  </div>
                )}
                {m.action?.ticket_platforms && (
                  <div className="mt-2.5 pt-2 border-t border-white/10 space-y-1">
                    <div className="text-[11px] font-semibold text-[#39ff14]">🎟️ Experience Tickets:</div>
                    <div className="grid grid-cols-2 gap-1 text-[10px]">
                      {Object.entries(m.action.ticket_platforms).map(([p, u]: any) => (
                        <a key={p} href={u} target="_blank" rel="noreferrer" className="capitalize text-[#00f0ff] underline truncate">{p}</a>
                      ))}
                    </div>
                  </div>
                )}
                {m.action?.ride_hailing && (
                  <div className="mt-2.5 pt-2 border-t border-white/10 space-y-1">
                    <div className="text-[11px] font-semibold text-[#00f0ff]">🚕 Cabs & Transit:</div>
                    <div className="grid grid-cols-2 gap-1 text-[10px]">
                      {Object.entries(m.action.ride_hailing).map(([p, u]: any) => (
                        <a key={p} href={u} target="_blank" rel="noreferrer" className="capitalize text-[#00f0ff] underline truncate">{p.replace('_', ' ')}</a>
                      ))}
                    </div>
                  </div>
                )}
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

      {/* Floating Action Button */}
      <button 
        onClick={openDrawer}
        className={`relative h-16 w-16 rounded-full bg-gradient-to-tr from-[#ff007f] to-[#00f0ff] flex items-center justify-center text-white shadow-[0_0_20px_rgba(255,0,127,0.5)] hover:shadow-[0_0_30px_rgba(0,240,255,0.8)] hover:scale-110 transition-all duration-300 z-[10000] group ${isOpen ? 'rotate-90' : 'rotate-0'}`}
      >
        <div className="absolute inset-0 rounded-full border border-white/40 bg-white/10 backdrop-blur-md"></div>
        {isOpen ? <X className="h-7 w-7 relative z-10 drop-shadow-[0_0_5px_rgba(255,255,255,0.8)]" /> : <MessageSquare className="h-7 w-7 relative z-10 drop-shadow-[0_0_5px_rgba(255,255,255,0.8)]" />}
        {!isOpen && (
          <span className="absolute top-0 right-0 h-4 w-4 bg-[#39ff14] rounded-full border-2 border-[#03050a] animate-pulse"></span>
        )}
      </button>
    </div>
  );
}
