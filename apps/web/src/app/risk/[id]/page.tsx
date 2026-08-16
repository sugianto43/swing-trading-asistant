import { TradePlanDetailClient } from "@/components/risk/trade-plan-detail-client";

export default async function TradePlanDetailPage(props: PageProps<"/risk/[id]">) {
  const { id } = await props.params;
  return <TradePlanDetailClient id={id} />;
}
