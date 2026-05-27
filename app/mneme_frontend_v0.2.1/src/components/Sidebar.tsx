import React from "react";
import { 
  FolderOpen, 
  Search, 
  Star, 
  Tag as TagIcon, 
  Settings, 
  Trash2, 
  Plus,
  ChevronLeft,
  Folder
} from "lucide-react";
import { cn } from "@/src/lib/utils";
import { ViewState } from "@/src/types";

interface SidebarProps {
  currentView: ViewState;
  onViewChange: (view: ViewState) => void;
  isCollapsed: boolean;
  setIsCollapsed: (collapsed: boolean) => void;
}

export default function Sidebar({ currentView, onViewChange, isCollapsed, setIsCollapsed }: SidebarProps) {
  const navItems = [
    { id: "daily-notes", label: "Daily Log", icon: FolderOpen },
    { id: "graph", label: "Graph View", icon: TagIcon },
    { id: "search", label: "Search", icon: Search },
    { id: "starred", label: "Starred", icon: Star },
  ];

  return (
    <aside 
      className={cn(
        "bg-white border-r border-slate-200 flex flex-col transition-all duration-300 relative z-20",
        isCollapsed ? "w-16" : "w-64"
      )}
    >
      <div className="p-4 border-b border-slate-100 flex items-center space-x-2">
        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-white font-bold shrink-0">
          M
        </div>
        {!isCollapsed && <span className="font-bold text-lg tracking-tight text-slate-900">Mneme v2.0</span>}
      </div>

      <div className="p-3 flex-1 space-y-6 overflow-hidden flex flex-col">
        <nav className="space-y-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => onViewChange(item.id as ViewState)}
              className={cn(
                "flex items-center space-x-2 w-full px-3 py-1.5 rounded-md text-sm transition-colors",
                currentView === item.id 
                  ? "bg-primary/5 text-primary font-medium" 
                  : "text-slate-600 hover:bg-slate-50"
              )}
            >
              <item.icon size={16} className="shrink-0" />
              {!isCollapsed && <span>{item.label}</span>}
              {!isCollapsed && item.id === "search" && (
                <span className="ml-auto text-[10px] bg-slate-100 px-1.5 py-0.5 rounded text-slate-400 font-mono">⌘K</span>
              )}
            </button>
          ))}
        </nav>

        {!isCollapsed && (
          <>
            <div>
              <h3 className="text-[10px] uppercase font-bold text-slate-400 px-3 mb-2 tracking-widest">Folders</h3>
              <div className="space-y-1">
                {["Project Phoenix", "Personal Garden", "Technical Stack"].map(folder => (
                  <div key={folder} className="flex items-center space-x-2 px-3 py-1 text-sm text-slate-600 hover:text-primary transition-colors cursor-pointer group">
                    <Folder size={14} className="text-slate-400 group-hover:text-primary transition-colors" />
                    <span>{folder}</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-[10px] uppercase font-bold text-slate-400 px-3 mb-2 tracking-widest">Recent Tags</h3>
              <div className="flex flex-wrap gap-1 px-2">
                <span className="text-[10px] bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded border border-indigo-100 cursor-pointer hover:bg-indigo-100 transition-colors">#research</span>
                <span className="text-[10px] bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded border border-emerald-100 cursor-pointer hover:bg-emerald-100 transition-colors">#active</span>
                <span className="text-[10px] bg-amber-50 text-amber-600 px-2 py-0.5 rounded border border-amber-100 cursor-pointer hover:bg-amber-100 transition-colors">#ideas</span>
              </div>
            </div>
          </>
        )}
      </div>

      <div className="p-4 border-t border-slate-100 flex items-center space-x-3">
        <div className="w-8 h-8 rounded-full bg-slate-200 overflow-hidden shrink-0">
          <img 
            alt="User" 
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuBU7H2nELzO7717fv6ixNnLHevOG0r54-YiXkjmSy9B8iwg9bOTain3NAH1ok5BnFCL-swoj33HNBn2RxB7wIP_lKOTwqUPOqG7jnUvpeT3Q8k6x8Mzw0JZ00_NDvWaoaOMmjqLpmkSk_qJmnnJUdFAgEpcZM_QpfzrM4nn9nnMnup5MDZPtsjUKv8O8D00nAh9y1_gGRnrrgm6bzo4p8KSXt2vhimklOjz7P6EOr7NOtLiFHCc5BPtQIauevBXvpbCULL7hoeENmZ0" 
            className="w-full h-full object-cover"
          />
        </div>
        {!isCollapsed && (
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-slate-900 truncate">juemimgcd</div>
            <div className="text-[10px] text-slate-400 truncate">Free Plan</div>
          </div>
        )}
        {!isCollapsed && (
          <button className="text-slate-400 hover:text-slate-600">
            <Settings size={14} />
          </button>
        )}
      </div>

      <button 
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-24 bg-white border border-slate-200 rounded-full p-1 shadow-sm z-50 hover:bg-slate-50 transition-all group"
      >
        <ChevronLeft 
          size={12} 
          className={cn("transition-transform text-slate-400", isCollapsed && "rotate-180")} 
        />
      </button>
    </aside>
  );
}
