import { Suspense } from "react";

import { AiPageContent } from "@/components/ai/ai-page-content";
import { Skeleton } from "@/components/ui/skeleton";

export default function AiPage() {
  return (
    <Suspense fallback={<Skeleton className="m-6 h-96" />}>
      <AiPageContent />
    </Suspense>
  );
}
