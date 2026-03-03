import { Suspense } from "react";
import { KanbanApp } from "@/components/KanbanApp";

export default function Home() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
      <KanbanApp />
    </Suspense>
  );
}
