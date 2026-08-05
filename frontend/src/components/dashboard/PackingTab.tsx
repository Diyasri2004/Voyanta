"use client";

import { useState } from "react";
import { Check, Plus } from "lucide-react";

export default function PackingTab({ trip }: { trip: any }) {
  const [items, setItems] = useState([
    { id: 1, text: "Passport & ID", packed: false },
    { id: 2, text: "Universal Adapter", packed: true },
    { id: 3, text: "Power Bank", packed: false },
    { id: 4, text: "Comfortable Sneakers", packed: false },
  ]);
  const [newItem, setNewItem] = useState("");

  const packedCount = items.filter(i => i.packed).length;
  const progress = Math.round((packedCount / items.length) * 100) || 0;

  const toggleItem = (id: number) => {
    setItems(items.map(i => i.id === id ? { ...i, packed: !i.packed } : i));
  };

  const addItem = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItem.trim()) return;
    setItems([...items, { id: Date.now(), text: newItem.trim(), packed: false }]);
    setNewItem("");
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Progress Bar */}
      <div className="bg-white/5 border border-white/10 p-4 rounded-xl">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs font-bold uppercase tracking-widest text-[#00f0ff]">Readiness</span>
          <span className="text-[#00f0ff] font-syne font-bold">{progress}%</span>
        </div>
        <div className="w-full bg-black/50 rounded-full h-2">
          <div className="bg-[#00f0ff] h-2 rounded-full transition-all duration-500 shadow-[0_0_10px_rgba(0,240,255,0.8)]" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <form onSubmit={addItem} className="flex gap-2">
        <input 
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          placeholder="Add gear..."
          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-[#39ff14]/50 focus:shadow-[0_0_10px_rgba(57,255,20,0.2)] transition-all"
        />
        <button type="submit" className="bg-[#39ff14]/20 text-[#39ff14] p-2 rounded-lg hover:bg-[#39ff14]/30">
          <Plus className="h-5 w-5" />
        </button>
      </form>

      <div className="flex flex-col gap-2">
        {items.map(item => (
          <button 
            key={item.id}
            onClick={() => toggleItem(item.id)}
            className={`flex items-center gap-3 p-3 rounded-lg border text-left transition-all ${
              item.packed 
                ? "bg-[#39ff14]/10 border-[#39ff14]/30 text-[#39ff14]" 
                : "bg-white/5 border-white/10 text-white hover:bg-white/10"
            }`}
          >
            <div className={`w-5 h-5 rounded flex items-center justify-center border ${
              item.packed ? "bg-[#39ff14] border-[#39ff14] text-black" : "border-white/30"
            }`}>
              {item.packed && <Check className="h-3 w-3" />}
            </div>
            <span className={`text-sm font-semibold ${item.packed ? "line-through opacity-70" : ""}`}>{item.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
