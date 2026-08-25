import React, { useState, useRef, useEffect } from 'react';
import { Send, X, ExternalLink, Sparkles, Navigation, Bed, Ticket, Compass } from 'lucide-react';

export default function VoyaChat({ destination = "", currency = "USD", activeItinerary = [], onAddStop = () => {} }) {
  const [isOpen, setIsOpen] = useState(false);
  
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

  const LANGUAGE_CONFIRMATIONS = {
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

  const selectLanguage = (code) => {
    setActiveLang(code);
    const confirmation = LANGUAGE_CONFIRMATIONS[code] || LANGUAGE_CONFIRMATIONS.en;
    setMessages(prev => [...prev, { role: "assistant", content: confirmation, action: null }]);
  };

  const getUserTimeContext = () => {
    return {
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
    };
  };

  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `${getTimeGreeting()}! Welcome to Voyanta 🙏`,
      action: null
    },
    {
      role: 'assistant',
      content: destination
        ? `I'm Voya. Ready to explore ${destination}! Whether you need inspiration or help with an ongoing booking, I've got you covered. What destination or plan is on your mind today?`
        : "I'm Voya. Whether you need inspiration for your next getaway or help with an ongoing booking, I've got you covered. What destination is on your mind today?",
      action: null
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

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
          content: destination 
            ? `I'm Voya. Ready to explore ${destination}! Whether you need inspiration or help with an ongoing booking, I've got you covered. What destination or plan is on your mind today?`
            : "I'm Voya. Whether you need inspiration for your next getaway or help with an ongoing booking, I've got you covered. What destination is on your mind today?",
          action: null
        }
      ]);
    }
  }, [destination]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isOpen]);

  const handleSend = async (customMessage) => {
    if (customMessage && typeof customMessage === 'object' && customMessage.preventDefault) {
      customMessage.preventDefault();
    }
    const userText = (typeof customMessage === 'string' ? customMessage : input).trim();
    if (!userText || loading) return;

    setInput('');
    const newHistory = [...messages, { role: 'user', content: userText, text: userText }];
    setMessages(newHistory);
    setLoading(true);

    const timeContext = getUserTimeContext();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText,
          destination: destination || '',
          currency: currency || 'USD',
          language: activeLang || 'en',
          user_time: timeContext.time,
          user_timezone: timeContext.timeZone,
          history: newHistory.map(m => ({ role: m.role, content: m.content || m.text || '' })),
          active_itinerary: activeItinerary || []
        })
      });

      const data = await response.json();
      const aiText = data.reply || data.response || data.message || ("I'm ready! How else can I assist your trip to " + (destination || 'your destination') + "?");

      if (data.action?.action === 'INSERT_STOP' && data.action?.stop) {
        onAddStop(data.action.stop);
      }

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: aiText,
          text: aiText,
          action: data.action || null
        }
      ]);
    } catch (err) {
      console.error("Voya Chat Error:", err);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: "I encountered a hiccup connecting to local services. Please try again!",
          text: "I encountered a hiccup connecting to local services. Please try again!",
          action: null
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 font-sans">
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 bg-gradient-to-r from-pink-600 to-rose-600 text-white px-5 py-3.5 rounded-full shadow-2xl hover:scale-105 transition-all duration-300 font-medium text-sm"
        >
          <Sparkles className="w-4 h-4 animate-pulse"/>
          <span>Ask Voya AI</span>
        </button>
      )}

      {isOpen && (
        <div className="w-[380px] sm:w-[420px] h-[580px] bg-[#11141a]/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
          <div className="flex items-center justify-between px-4 py-3.5 border-b border-white/10 bg-white/5">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-pink-500 to-rose-600 flex items-center justify-center text-white shadow-md">
                <Sparkles className="w-4 h-4"/>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Voya Concierge</h3>
                <p className="text-[11px] text-gray-400">{destination ? `Grounded in ${destination}` : 'Ready for your journey'}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={activeLang}
                onChange={(e) => selectLanguage(e.target.value)}
                className="bg-black/60 text-pink-400 border border-white/10 text-[10px] rounded-lg px-1.5 py-1 focus:outline-none cursor-pointer"
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
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors"
              >
                <X className="w-5 h-5"/>
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs text-gray-200">
            {messages.map((m, idx) => (
              <div key={idx} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'} animate-fadeInUp`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-gradient-to-r from-pink-600 to-rose-600 text-white rounded-br-none'
                      : 'bg-white/10 text-gray-100 rounded-bl-none border border-white/5'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>

                  {/* Accommodations Badges */}
                  {m.action?.booking_platforms && (
                    <div className="mt-3 pt-2.5 border-t border-white/10 space-y-1.5">
                      <div className="flex items-center gap-1 text-[11px] font-semibold text-pink-400">
                        <Bed className="w-3.5 h-3.5"/> Book Stays:
                      </div>
                      <div className="grid grid-cols-2 gap-1.5">
                        {Object.entries(m.action.booking_platforms).map(([platform, url]) => (
                          <a
                            key={platform}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-black/40 hover:bg-pink-600/30 border border-white/10 text-[10px] text-gray-200 transition-colors"
                          >
                            <span className="capitalize">{platform.replace('_', ' ')}</span>
                            <ExternalLink className="w-2.5 h-2.5 text-gray-400"/>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Tour & Attraction Tickets */}
                  {m.action?.ticket_platforms && (
                    <div className="mt-3 pt-2.5 border-t border-white/10 space-y-1.5">
                      <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
                        <Ticket className="w-3.5 h-3.5"/> Experience Tickets:
                      </div>
                      <div className="grid grid-cols-2 gap-1.5">
                        {Object.entries(m.action.ticket_platforms).map(([platform, url]) => (
                          <a
                            key={platform}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-black/40 hover:bg-emerald-600/30 border border-white/10 text-[10px] text-gray-200 transition-colors"
                          >
                            <span className="capitalize">{platform}</span>
                            <ExternalLink className="w-2.5 h-2.5 text-gray-400"/>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Cabs & Transit Hubs */}
                  {m.action?.ride_hailing && (
                    <div className="mt-3 pt-2.5 border-t border-white/10 space-y-1.5">
                      <div className="flex items-center gap-1 text-[11px] font-semibold text-sky-400">
                        <Navigation className="w-3.5 h-3.5"/> Cabs & Transit:
                      </div>
                      <div className="grid grid-cols-2 gap-1.5">
                        {Object.entries(m.action.ride_hailing).map(([platform, url]) => (
                          <a
                            key={platform}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-black/40 hover:bg-sky-600/30 border border-white/10 text-[10px] text-gray-200 transition-colors"
                          >
                            <span className="capitalize">{platform.replace('_', ' ')}</span>
                            <ExternalLink className="w-2.5 h-2.5 text-gray-400"/>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Multi-City Rail & Flight Legs */}
                  {m.action?.itinerary_legs && (
                    <div className="mt-3 pt-2.5 border-t border-white/10 space-y-2">
                      <div className="flex items-center gap-1 text-[11px] font-semibold text-amber-400">
                        <Compass className="w-3.5 h-3.5"/> Transit Connections:
                      </div>
                      {m.action.itinerary_legs.map((leg, lIdx) => (
                        <div key={lIdx} className="p-2 rounded-lg bg-black/30 border border-white/5 space-y-1">
                          <div className="text-[11px] font-medium text-white">{leg.from} → {leg.to}</div>
                          <div className="flex gap-2 text-[10px]">
                            <a href={leg.train_booking} target="_blank" rel="noreferrer" className="text-pink-400 underline">Trainline</a>
                            <a href={leg.flight_booking} target="_blank" rel="noreferrer" className="text-sky-400 underline">Skyscanner</a>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-gray-400 text-xs italic">
                <Sparkles className="w-3.5 h-3.5 animate-spin text-pink-500"/>
                <span>Voya is curating authentic live links...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSend} className="p-3 border-t border-white/10 bg-white/5 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about hotels, Klook tickets, cabs, or weather..."
              className="flex-1 bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-pink-500 transition-colors"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="bg-gradient-to-r from-pink-600 to-rose-600 disabled:opacity-40 text-white p-2.5 rounded-xl hover:scale-105 transition-all"
            >
              <Send className="w-3.5 h-3.5"/>
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
