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

  const getInitialGreeting = (dest) => {
    const timeGreeting = getTimeGreeting();
    const destinationGreeting = dest ? `${timeGreeting} from ${dest}!` : `${timeGreeting}!`;
    return `${destinationGreeting}\n\nHey there! Welcome to Voyanta 🙏😄\nI am Voya, your virtual assistant. I can help you with a lot of things, just let me know what you need!`;
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
      content: getInitialGreeting(destination),
      action: null
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (messages.length === 1 && messages[0].role === 'assistant') {
      setMessages([
        {
          role: 'assistant',
          content: getInitialGreeting(destination),
          action: null
        }
      ]);
    }
  }, [destination]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isOpen]);

  const handleSend = async (e) => {
    e?.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput('');
    const newHistory = [...messages, { role: 'user', content: userText }];
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
          user_time: timeContext.time,
          user_timezone: timeContext.timeZone,
          history: newHistory.map(m => ({ role: m.role, content: m.content })),
          active_itinerary: activeItinerary || []
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const data = await response.json();
      if (data.status === 'success') {
        if (data.action?.action === 'INSERT_STOP' && data.action?.stop) {
          onAddStop(data.action.stop);
        }

        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: data.reply, action: data.action }
        ]);
      } else {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: data.reply || "I encountered an issue connecting to local services.", action: null }
        ]);
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: "Network error reaching Voya services. Please try again.", action: null }
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
            <button
              onClick={() => setIsOpen(false)}
              className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors"
            >
              <X className="w-5 h-5"/>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs text-gray-200">
            {messages.map((m, idx) => (
              <div key={idx} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
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
