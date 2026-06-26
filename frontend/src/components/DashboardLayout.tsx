"use client";

import { motion } from 'framer-motion';
import { useState } from 'react';

export default function DashboardLayout({ 
  mapComponent, 
  timelineComponent 
}: { 
  mapComponent: React.ReactNode, 
  timelineComponent: React.ReactNode 
}) {
  const [expandedSlot, setExpandedSlot] = useState<string | null>(null);

  return (
    <div className="flex h-screen w-full bg-brand-dark overflow-hidden text-white">
      {/* Left Column: Control Panel */}
      <motion.div 
        initial={{ width: '40%' }}
        animate={{ width: expandedSlot ? '50%' : '40%' }}
        transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
        className="h-full bg-brand-surface border-r border-gray-800 shadow-2xl flex flex-col relative z-10"
      >
        <div className="p-6 border-b border-gray-800 flex justify-between items-center">
          <h1 className="text-2xl font-bold tracking-tight">Voyanta <span className="text-brand-accent">.</span></h1>
          {/* Tabs: Itinerary, Budget, Packing */}
          <div className="flex space-x-4 text-sm font-medium text-gray-400">
            <button className="text-white border-b-2 border-brand-accent pb-1">Itinerary</button>
            <button className="hover:text-white transition-colors pb-1">Budget</button>
            <button className="hover:text-white transition-colors pb-1">Packing</button>
          </div>
        </div>
        
        {/* Timeline Content */}
        <div className="flex-1 overflow-y-auto p-6 scrollbar-hide">
          {timelineComponent}
        </div>
      </motion.div>

      {/* Right Column: Geospatial View */}
      <div className="flex-1 relative">
        {mapComponent}
        
        {/* Example glowing festival badge overlay */}
        <div className="absolute top-6 left-6 z-20 flex items-center space-x-2 bg-black/60 backdrop-blur-md px-4 py-2 rounded-full border border-gray-700">
          <span className="relative flex h-3 w-3">
            <span className="animate-festival-ping absolute inline-flex h-full w-full rounded-full bg-brand-accent opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-accent"></span>
          </span>
          <span className="text-sm font-medium">Live: Kyoto Lantern Festival (2km away)</span>
        </div>
      </div>
    </div>
  );
}
