import { Suspense } from "react";

import { PositionsPageContent } from "@/components/positions/positions-page-content";
import { Skeleton } from "@/components/ui/skeleton";

export default function PositionsPage() {
  return (
    <Suspense fallback={<Skeleton className="m-6 h-96" />}>
      <PositionsPageContent />
    </Suspense>
  );
}
