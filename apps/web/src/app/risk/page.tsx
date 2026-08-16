import { Suspense } from "react";

import { RiskPageContent } from "@/components/risk/risk-page-content";
import { Skeleton } from "@/components/ui/skeleton";

export default function RiskPage() {
  return (
    <Suspense fallback={<Skeleton className="m-6 h-96" />}>
      <RiskPageContent />
    </Suspense>
  );
}
