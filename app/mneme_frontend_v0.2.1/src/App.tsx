/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import DailyNotesView from "./components/DailyNotesView";
import EditorView from "./components/EditorView";
import GraphView from "./components/GraphView";
import LoginView from "./components/LoginView";
import SettingsModal from "./components/SettingsModal";
import CommandPalette from "./components/CommandPalette";
import { ViewState } from "./types";
import { cn } from "./lib/utils";

export default function App() {
  const [view, setView] = useState<ViewState>("login");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsCommandPaletteOpen(prev => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  if (view === "login") {
    return <LoginView onLogin={() => setView("daily-notes")} />;
  }

  const getTitle = () => {
    switch (view) {
      case "daily-notes": return "Vault / Daily Notes";
      case "editor": return "Vault / Research / AI Ethics";
      case "graph": return "Knowledge Graph / Network Overview";
      default: return "Mneme";
    }
  };

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden relative selection:bg-primary/20">
      <Sidebar 
        currentView={view} 
        onViewChange={(v) => {
          if (v === "search") {
            setIsCommandPaletteOpen(true);
          } else {
            setView(v);
          }
        }} 
        isCollapsed={isSidebarCollapsed}
        setIsCollapsed={setIsSidebarCollapsed}
      />

      <div className="flex-1 flex flex-col min-w-0 relative">
        <TopBar 
          title={getTitle()} 
          onSettingsClick={() => setIsSettingsOpen(true)} 
        />
        
        <main className="flex-1 overflow-hidden">
          {view === "daily-notes" && (
            <div 
              className="h-full cursor-pointer" 
              onClick={(e) => {
                // Mock behavior: clicking a note goes to editor
                if ((e.target as HTMLElement).closest('article')) {
                  setView("editor");
                }
              }}
            >
              <DailyNotesView />
            </div>
          )}
          {view === "editor" && <EditorView />}
          {view === "graph" && <GraphView />}
        </main>

        <footer className="h-10 border-t border-slate-100 bg-white px-6 flex items-center justify-between shrink-0 z-10">
          <div className="text-[10px] text-slate-400 font-mono">Markdown • UTF-8 • 432 Words</div>
          <div className="flex items-center space-x-4">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-[10px] text-slate-400 uppercase tracking-widest leading-none">Synced to Vault</span>
          </div>
        </footer>
      </div>

      <CommandPalette 
        isOpen={isCommandPaletteOpen} 
        onClose={() => setIsCommandPaletteOpen(false)} 
      />
      
      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
      />
    </div>
  );
}
