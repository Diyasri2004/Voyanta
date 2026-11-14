"use client";

import { useState, useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, Send } from "lucide-react";
import HeaderMenu from "@/components/ui/HeaderMenu";
import VoyaMark from "./VoyaMark";
import { TypedText } from "./RichText";

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
    fresh?: boolean;
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
  const scrollRef = useRef<HTMLDivElement>(null);
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
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isLoading, isOpen]);

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
    "Offbeat spots that are not on my cards",
    "Events happening during my trip",
    "Top local food spots and budget",
    "Rainy day backup plan",
  ];

  /** Names of places already shown as cards, so Voya can offer different ones when asked for more. */
  const collectShownPlaces = (): string[] => {
    const out: string[] = [];
    try {
      const dest = trip?.destination;
      if (dest) {
        for (let i = 0; i < sessionStorage.length; i++) {
          const k = sessionStorage.key(i) || "";
          if (k.startsWith(`voyanta_${dest}_`)) {
            const arr = JSON.parse(sessionStorage.getItem(k) || "[]");
            if (Array.isArray(arr)) arr.forEach((x: any) => (x?.title || x?.name) && out.push(x.title || x.name));
          }
        }
      }
    } catch (_) {}
    (trip?.itinerary || []).forEach((s: any) => s?.title && out.push(s.title));
    return Array.from(new Set(out)).slice(0, 80);
  };

  const sendMessage = async (customMessage?: any, presetMessage?: string) => {
    let userMsg = "";
    if (typeof customMessage === "string") {
      userMsg = customMessage;
    } else if (presetMessage) {
      userMsg = presetMessage;
    } else if (customMessage && customMessage.preventDefault) {
      customMessage.preventDefault();
      userMsg = input.trim();
    } else {
      userMsg = input.trim();
    }
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
          language: activeLang || 'en',
          user_time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          user_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
          history: newMessages.map(m => ({ role: m.role, content: m.content || m.text || '' })),
          active_itinerary: trip?.itinerary || [],
          trip_start: trip?.start_date || '',
          trip_end: trip?.end_date || '',
          shown_places: collectShownPlaces()
        })
      });

      if (!response.ok) {
        console.error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const aiText = data.reply || data.response || data.message || ("I'm ready! How else can I assist your trip to " + (trip?.destination || 'your destination') + "?");

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: aiText,
          text: aiText,
          action: data.action || null,
          fresh: true
        }
      ]);
    } catch (err) {
      console.error("Voya Chat Fetch Error:", err);
      setMessages(prev => [
        ...prev,
        {
          role: "assistant",
          content: "I encountered a hiccup connecting to local services. Please try again!",
          text: "I encountered a hiccup connecting to local services. Please try again!",
          action: null
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const LANG_OPTIONS = [
    { value: "en", label: "English", hint: "EN" },
    { value: "hi", label: "Hindi (Hinglish)", hint: "HI" },
    { value: "ta", label: "Tamil (Tanglish)", hint: "TA" },
    { value: "te", label: "Telugu (Teluglish)", hint: "TE" },
    { value: "kn", label: "Kannada (Kanglish)", hint: "KN" },
    { value: "ml", label: "Malayalam (Manglish)", hint: "ML" },
    { value: "bn", label: "Bengali (Banglish)", hint: "BN" },
    { value: "ar", label: "Arabic (Arabizi)", hint: "AR" },
    { value: "es", label: "Spanish", hint: "ES" },
    { value: "fr", label: "French", hint: "FR" },
    { value: "de", label: "German", hint: "DE" },
    { value: "zh", label: "Chinese (Pinyin)", hint: "ZH" },
    { value: "ru", label: "Russian (Translit)", hint: "RU" },
  ];

  const linkGroup = (title: string, entries: Record<string, string>) => (
    <div className="mt-3 border-t border-white/10 pt-2.5">
      <div className="mb-1.5 text-[11px] font-semibold text-[#ffc36b]">{title}</div>
      <div className="flex flex-wrap gap-1.5">
        {Object.entries(entries).map(([p, u]) => (
          <a
            key={p}
            href={u}
            target="_blank"
            rel="noreferrer"
            className="rounded-full border border-[#ffc36b]/30 bg-[#ffc36b]/10 px-2.5 py-1 text-[11px] font-medium capitalize text-[#ffd89a] transition hover:bg-[#ffc36b]/20"
          >
            {p.replace("_", " ")}
          </a>
        ))}
      </div>
    </div>
  );

  return (
    <div
      className="pointer-events-auto fixed right-4 z-[9999] flex flex-col items-end sm:right-6"
      style={{ bottom: "max(1rem, env(safe-area-inset-bottom))" }}
    >
      {/* Chat panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            role="dialog"
            aria-label="Voya travel assistant"
            initial={{ opacity: 0, y: 24, rotateX: -14, scale: 0.94 }}
            animate={{ opacity: 1, y: 0, rotateX: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.96 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            style={{ transformPerspective: 1200, transformOrigin: "bottom right" }}
            className="absolute bottom-full right-0 mb-4 flex h-[34rem] max-h-[calc(100svh-7.5rem)] w-[calc(100vw-2rem)] flex-col rounded-3xl border border-white/10 bg-[#070c19]/90 shadow-[0_40px_90px_-20px_rgba(0,0,0,0.9),0_0_60px_-20px_rgba(255,176,80,0.35)] backdrop-blur-2xl sm:w-[26rem]"
          >
            {/* ambient glow */}
            <div aria-hidden className="pointer-events-none absolute -top-px left-8 right-8 h-px bg-gradient-to-r from-transparent via-[#ffc36b]/70 to-transparent" />

            {/* Header */}
            <div className="relative z-20 flex items-center justify-between gap-3 border-b border-white/[0.07] px-4 py-3.5">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[#ffc36b]/30 bg-[#ffc36b]/10 text-[#7fd6ff] shadow-[0_0_28px_-6px_rgba(255,195,107,0.6)]">
                  <VoyaMark size={30} />
                </div>
                <div>
                  <h3 className="font-display text-2xl leading-none text-[#f6efe2]">Voya</h3>
                  <p className="mt-1 flex items-center gap-1.5 text-[11px] text-[#8b95ab]">
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#7fd6ff]/70" />
                      <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#7fd6ff]" />
                    </span>
                    Travel guide · online
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <HeaderMenu
                  size="sm"
                  icon="globe"
                  ariaLabel="Chat language"
                  value={activeLang}
                  display={activeLang.toUpperCase()}
                  onChange={selectLanguage}
                  options={LANG_OPTIONS}
                />
                <button
                  onClick={() => setIsOpen(false)}
                  aria-label="Close chat"
                  className="flex h-8 w-8 items-center justify-center rounded-full text-[#8b95ab] transition hover:bg-white/10 hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="hide-scrollbar flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4" ref={scrollRef}>
              {messages.map((m: any, i: number) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                  className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[86%] px-4 py-3 text-[13.5px] leading-relaxed ${
                      m.role === "user"
                        ? "rounded-2xl rounded-br-md bg-[linear-gradient(115deg,#ffe2ae,#ffc36b_55%,#ff9d5c)] font-medium text-[#1b1206] shadow-[0_10px_30px_-12px_rgba(255,176,80,0.7)]"
                        : "rounded-2xl rounded-bl-md border border-white/10 bg-white/[0.05] text-[#e4e9f4]"
                    }`}
                  >
                    {m.role === "user" ? (
                      <p className="whitespace-pre-wrap">{m.content || m.text}</p>
                    ) : (
                      <TypedText text={m.content || m.text || ""} animate={!!m.fresh && i === messages.length - 1} />
                    )}
                    {m.action?.events?.length > 0 && (
                      <div className="mt-3 space-y-2 border-t border-white/10 pt-2.5">
                        <div className="text-[11px] font-semibold text-[#ffc36b]">Events</div>
                        {m.action.events.slice(0, 5).map((ev: any, k: number) => (
                          <div key={k} className="flex items-start justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.04] p-2.5">
                            <div className="min-w-0">
                              <div className="truncate text-[13px] font-semibold text-[#f6efe2]">{ev.title}</div>
                              <div className="mt-0.5 text-[11.5px] text-[#9aa5bb]">
                                {[ev.when, ev.venue, ev.price].filter(Boolean).join(" · ")}
                              </div>
                              {ev.note && <div className="mt-0.5 text-[11px] text-[#7fd6ff]">{ev.note}</div>}
                            </div>
                            {ev.book_url && (
                              <a href={ev.book_url} target="_blank" rel="noreferrer noopener"
                                className="shrink-0 rounded-full bg-[linear-gradient(115deg,#ffe2ae,#ffc36b_55%,#ff9d5c)] px-3 py-1.5 text-[11px] font-bold text-[#1b1206]">
                                Book
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    {m.action?.places?.length > 0 && (
                      <div className="mt-3 space-y-2 border-t border-white/10 pt-2.5">
                        <div className="text-[11px] font-semibold text-[#ffc36b]">{m.action.places.length === 1 ? "Location" : "More places"}</div>
                        {m.action.places.slice(0, 5).map((pl: any, k: number) => (
                          <div key={k} className="rounded-xl border border-white/10 bg-white/[0.04] p-2.5">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="truncate text-[13px] font-semibold text-[#f6efe2]">{pl.name}</div>
                                {(pl.address || pl.area) && <div className="line-clamp-2 text-[11.5px] text-[#9aa5bb]">{pl.address || pl.area}</div>}
                              </div>
                              <div className="flex shrink-0 gap-1.5">
                                <a href={pl.maps_url} target="_blank" rel="noreferrer noopener"
                                  className="rounded-full border border-white/15 bg-white/[0.06] px-2.5 py-1 text-[11px] font-semibold text-[#cbd3e3]">Map</a>
                                {pl.directions_url && (
                                  <a href={pl.directions_url} target="_blank" rel="noreferrer noopener"
                                    className="rounded-full border border-[#ffc36b]/40 bg-[#ffc36b]/10 px-2.5 py-1 text-[11px] font-semibold text-[#ffc36b]">Directions</a>
                                )}
                                {pl.website && (
                                  <a href={pl.website} target="_blank" rel="noreferrer noopener"
                                    className="rounded-full border border-[#7fd6ff]/30 bg-[#7fd6ff]/10 px-2.5 py-1 text-[11px] font-semibold text-[#7fd6ff]">Site</a>
                                )}
                              </div>
                            </div>
                            {pl.about && <p className="mt-1 line-clamp-2 text-[11.5px] leading-snug text-[#8b95ab]">{pl.about}</p>}
                          </div>
                        ))}
                      </div>
                    )}
                    {m.action?.event_platforms && linkGroup("Book events", m.action.event_platforms)}
                    {m.action?.booking_platforms && linkGroup("Stays", m.action.booking_platforms)}
                    {m.action?.ticket_platforms && linkGroup("Experience tickets", m.action.ticket_platforms)}
                    {m.action?.ride_hailing && linkGroup("Cabs and transit", m.action.ride_hailing)}
                  </div>
                </motion.div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="flex gap-1.5 rounded-2xl rounded-bl-md border border-white/10 bg-white/[0.05] px-4 py-3.5">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-[#ffc36b]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-[#ffc36b] [animation-delay:0.15s]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-[#ffc36b] [animation-delay:0.3s]" />
                  </div>
                </div>
              )}
            </div>

            {/* Quick prompts */}
            <div className="hide-scrollbar flex gap-2 overflow-x-auto px-4 pb-3">
              {SUGGESTIONS.map((sug, idx) => (
                <button
                  key={idx}
                  onClick={() => sendMessage(undefined, sug)}
                  className="glass whitespace-nowrap rounded-full px-3.5 py-2 text-[11.5px] font-medium text-[#cbd3e3] transition hover:border-[#ffc36b]/40 hover:text-white"
                >
                  {sug}
                </button>
              ))}
            </div>

            {/* Input */}
            <form onSubmit={(e) => sendMessage(e)} className="border-t border-white/[0.07] p-3">
              <div className="flex items-center rounded-full border border-white/10 bg-white/[0.04] pr-1.5 transition focus-within:border-[#ffc36b]/50 focus-within:shadow-[0_0_20px_-6px_rgba(255,195,107,0.5)]">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask Voya anything about your trip"
                  className="h-12 flex-1 bg-transparent px-4 text-base text-white outline-none placeholder:text-white/35 sm:text-sm"
                />
                <button
                  type="submit"
                  disabled={!input.trim() || isLoading}
                  aria-label="Send message"
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-[linear-gradient(115deg,#ffe2ae,#ffc36b_55%,#ff9d5c)] text-[#1b1206] transition hover:brightness-105 active:scale-95 disabled:opacity-40"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Launcher: glowing orb with Voya's emblem */}
      <motion.button
        onClick={isOpen ? () => setIsOpen(false) : openDrawer}
        aria-label={isOpen ? "Close Voya chat" : "Open Voya travel assistant"}
        whileHover={{ scale: 1.08, rotate: isOpen ? 0 : -6 }}
        whileTap={{ scale: 0.94 }}
        className="group relative z-[10000] flex h-16 w-16 items-center justify-center rounded-full border border-white/25 bg-[radial-gradient(circle_at_30%_25%,#2a3350,#0a1020_70%)] text-[#7fd6ff] shadow-[0_0_0_1px_rgba(255,195,107,0.35),0_18px_50px_-10px_rgba(255,176,80,0.7)] sm:h-[4.5rem] sm:w-[4.5rem]"
      >
        <span aria-hidden className="absolute -inset-1.5 rounded-full bg-[conic-gradient(from_0deg,transparent,rgba(255,195,107,0.55),transparent_60%)] opacity-70 blur-md animate-spin [animation-duration:6s]" />
        <span className="relative">
          {isOpen ? <X className="h-7 w-7 text-[#ffd89a]" /> : <VoyaMark size={38} />}
        </span>
        {!isOpen && (
          <span className="absolute right-0.5 top-0.5 h-3.5 w-3.5 rounded-full border-2 border-[#070c19] bg-[#ffc36b]">
            <span className="absolute inset-0 animate-ping rounded-full bg-[#ffc36b]/70" />
          </span>
        )}
      </motion.button>
    </div>
  );
}
