import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Search, Terminal, FileText, CornerDownLeft } from "lucide-react";
import { cn } from "@/src/lib/utils";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState("");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        // Toggle handled by parent
      }
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!isOpen) return null;

  const results = [
    { id: 1, type: "file", title: "Cognitive Load Theory", path: "Digital Garden/Psychology/Learning/Cognitive Load Theory.md" },
    { id: 2, type: "file", title: "Metacognition Strategies", path: "Digital Garden/Education/Metacognition Strategies.md" },
    { id: 3, type: "file", title: "Cognitive Behavioral Therapy Notes", path: "Digital Garden/Psychology/Therapy/CBT Notes.md" },
  ].filter(item => item.title.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-32 px-4">
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="absolute inset-0 bg-on-surface/20 backdrop-blur-sm" 
      />
      
      <motion.div 
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="relative w-full max-w-2xl bg-surface-container-lowest rounded-lg border border-outline-variant shadow-2xl flex flex-col max-h-[600px] overflow-hidden"
      >
        <div className="flex items-center px-4 py-3 border-b border-outline-variant">
          <Search size={20} className="text-primary mr-3" />
          <input 
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 bg-transparent border-none focus:ring-0 text-body-lg text-text-primary placeholder-text-muted"
            placeholder="Search files, commands, or settings..."
          />
          <span className="font-label-mono text-[10px] text-text-muted bg-surface-container-low px-1.5 py-0.5 rounded border border-outline-variant">
            ESC
          </span>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {results.length > 0 && (
            <div className="px-4 py-2">
              <h3 className="font-label-mono text-[10px] text-text-muted uppercase tracking-widest">Files</h3>
            </div>
          )}

          {results.map((item, idx) => (
            <div 
              key={item.id}
              className={cn(
                "group flex items-center justify-between px-4 py-3 cursor-pointer border-l-2",
                idx === 0 ? "bg-accent-soft border-primary" : "border-transparent hover:bg-surface-container-high"
              )}
            >
              <div className="flex items-center gap-3">
                <FileText size={18} className={idx === 0 ? "text-primary" : "text-text-muted"} />
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-text-primary">
                    {item.title}
                  </span>
                  <span className="font-label-mono text-[10px] text-text-muted mt-0.5">
                    {item.path}
                  </span>
                </div>
              </div>
              {idx === 0 && (
                <CornerDownLeft size={14} className="text-text-muted" />
              )}
            </div>
          ))}

          <div className="px-4 py-2 mt-2 border-t border-outline-variant pt-4">
            <h3 className="font-label-mono text-[10px] text-text-muted uppercase tracking-widest">Commands</h3>
          </div>

          <div className="group flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-surface-container-high border-l-2 border-transparent">
            <div className="flex items-center gap-3">
              <Terminal size={18} className="text-text-muted" />
              <span className="text-sm text-text-primary">Create new note: "{query || "unnamed"}"</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="font-label-mono text-[10px] text-text-muted bg-surface-container-low px-1.5 py-0.5 rounded border border-outline-variant tracking-tighter">⌘ N</span>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between px-4 py-2 border-t border-outline-variant bg-surface-container-low">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1 font-label-mono text-[10px] text-text-muted">
              <span className="bg-surface-container-high px-1 rounded">↑</span>
              <span className="bg-surface-container-high px-1 rounded">↓</span>
              <span className="ml-1">to navigate</span>
            </div>
            <div className="flex items-center gap-1 font-label-mono text-[10px] text-text-muted">
              <span className="bg-surface-container-high px-1 rounded">↵</span>
              <span className="ml-1">to select</span>
            </div>
          </div>
          <div className="font-label-mono text-[10px] text-text-muted">
            {results.length + 1} results
          </div>
        </div>
      </motion.div>
    </div>
  );
}
