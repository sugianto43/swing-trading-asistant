import type { PositionStatus } from "@/lib/queries/positions";

export const STATUS_BADGE_VARIANT: Record<
  PositionStatus,
  "secondary" | "outline" | "destructive"
> = {
  PLANNED: "outline",
  OPEN: "secondary",
  PARTIALLY_CLOSED: "secondary",
  CLOSED: "outline",
  CANCELLED: "destructive",
};
