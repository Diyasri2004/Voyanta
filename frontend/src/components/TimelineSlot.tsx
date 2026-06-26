"use client";

import { motion } from 'framer-motion';

export interface TimelineItem {
  id: string;
  title: string;
  startTime: string;
  endTime: string;
}

export default function TimelineSlot({ 
  item, 
  isConflicted 
}: { 
  item: TimelineItem, 
  isConflicted: boolean 
}) {
  return (
    <motion.div
      layout
      drag="y"
      dragConstraints={{ top: 0, bottom: 0 }}
      whileHover={{ scale: 1.02 }}
      whileDrag={{ scale: 1.05, zIndex: 10, boxShadow: "0px 10px 20px rgba(0,0,0,0.5)" }}
      className={`relative p-4 mb-4 rounded-xl cursor-grab active:cursor-grabbing border transition-colors ${
        isConflicted ? 'bg-red-900/20 border-red-500' : 'bg-brand-dark border-gray-800 hover:border-gray-600'
      }`}
    >
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold text-lg">{item.title}</h3>
          <p className="text-sm text-gray-400">{item.startTime} - {item.endTime}</p>
        </div>
        {isConflicted && (
          <div className="bg-red-500 text-white text-xs px-2 py-1 rounded font-bold">
            Transit Conflict
          </div>
        )}
      </div>
    </motion.div>
  );
}
