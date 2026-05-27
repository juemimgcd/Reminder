import React from "react";
import { Settings } from "lucide-react";
import { cn } from "@/src/lib/utils";

interface TopBarProps {
  title: string;
  onSettingsClick?: () => void;
}

export default function TopBar({ title, onSettingsClick }: TopBarProps) {
  return (
    <header className="h-12 border-b border-slate-100 flex items-center justify-between px-6 bg-white shrink-0 z-10">
      <div className="flex items-center space-x-4 text-[11px] text-slate-400 font-medium">
        <span>Vault</span>
        <span className="opacity-40">/</span>
        <span className="truncate max-w-[200px]">{title}</span>
      </div>
      
      <div className="flex items-center space-x-2">
        <button className="px-3 py-1 border border-slate-200 rounded text-[11px] text-slate-600 hover:bg-slate-50 transition-colors">
          Share
        </button>
        <button 
          className="px-3 py-1 bg-primary text-white rounded text-[11px] font-semibold hover:bg-primary/90 transition-colors"
          onClick={onSettingsClick}
        >
          Publish
        </button>
      </div>
    </header>
  );
}
