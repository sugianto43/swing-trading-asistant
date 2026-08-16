import { PositionDetailClient } from "@/components/positions/position-detail-client";

export default async function PositionDetailPage(props: PageProps<"/positions/[id]">) {
  const { id } = await props.params;
  return <PositionDetailClient id={id} />;
}
