import React from "react";
import { ChevronLeft, ChevronRight, Activity } from "lucide-react";
import { cn } from "@/src/lib/utils";

export default function DailyNotesView() {
  const notes = [
    {
      id: "1",
      date: "Oct 27, 2023",
      content: "Exploring the convergence of bi-directional linking and mental graph visualization for personal knowledge management. Indexed 10k+ files successfully.",
      tags: ["#research", "#pkm"],
      isLatest: true
    },
    {
      id: "2",
      date: "Oct 26, 2023",
      content: "The core philosophy is based on the Zettelkasten method, where every node is a small, atomic idea that connects to others.",
      tags: ["#ideas"],
      isLatest: false
    },
    {
      id: "3",
      date: "Oct 25, 2023",
      content: "Zettelkasten vs Hierarchical Storage: A deep dive into rhizomatic structures and why folders are just a representation, not the logic.",
      tags: ["#technical"],
      isLatest: false
    }
  ];

  return (
    <div className="flex-1 p-12 flex flex-col lg:flex-row gap-12 max-w-[1280px] mx-auto w-full overflow-y-auto bg-white">
      <div className="flex-1 max-w-[800px]">
        <div className="mb-10">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">Daily Log</h1>
          <p className="text-sm text-slate-500 font-medium tracking-tight">Structured stream of consciousness.</p>
        </div>

        <div className="space-y-10">
          {notes.map((note) => (
            <article key={note.id} className="group cursor-text">
              <div className="flex items-center gap-4 mb-4">
                <span className={cn(
                  "text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded border transition-colors",
                  note.isLatest 
                    ? "bg-indigo-50 text-indigo-600 border-indigo-200" 
                    : "bg-slate-50 text-slate-400 border-slate-200"
                )}>
                  {note.date}
                </span>
                <div className="h-[1px] flex-1 bg-slate-100" />
              </div>
              
              <div className="pl-4 border-l-4 border-slate-100 group-hover:border-primary transition-colors py-2">
                <p className="text-slate-700 leading-relaxed text-lg font-normal mb-6">
                  {note.content}
                </p>
                {note.tags.length > 0 && (
                  <div className="flex gap-1">
                    {note.tags.map(tag => (
                      <span key={tag} className="text-[10px] bg-slate-50 text-slate-500 px-2 py-0.5 rounded border border-slate-200">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      </div>

      <div className="w-full lg:w-[280px] shrink-0 space-y-10">
        <div>
          <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">Calendar</h4>
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
            <div className="grid grid-cols-7 gap-1 text-center font-mono text-[9px] text-slate-400 mb-2 font-bold">
              {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((d, i) => <div key={`${d}-${i}`}>{d}</div>)}
            </div>
            <div className="grid grid-cols-7 gap-1 text-center text-[11px]">
              {[...Array(30)].map((_, i) => (
                <div 
                  key={i} 
                  className={cn(
                    "w-7 h-7 flex items-center justify-center rounded cursor-pointer transition-colors",
                    i + 1 === 27 ? "bg-primary text-white font-bold" : "hover:bg-slate-200 text-slate-600"
                  )}
                >
                  {i + 1}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div>
          <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">Backlinks</h4>
          <div className="space-y-2">
            {[1, 2].map(i => (
              <div key={i} className="p-3 bg-white border border-slate-200 rounded text-xs hover:border-indigo-300 transition-colors group">
                <div className="font-semibold text-indigo-600 truncate group-hover:text-primary transition-colors">Digital Garden Architecture</div>
                <div className="text-[10px] text-slate-400 mt-1 line-clamp-2">Exploring the convergence of multi-agent environments...</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
