export type ViewState = "login" | "daily-notes" | "editor" | "graph" | "search" | "starred";

export interface Note {
  id: string;
  title: string;
  content: string;
  createdAt: string;
  tags: string[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: "document" | "tag" | "concept";
}

export interface GraphLink {
  source: string;
  target: string;
}
