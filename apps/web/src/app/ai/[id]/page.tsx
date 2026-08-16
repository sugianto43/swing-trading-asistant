import { SnapshotDetailClient } from "@/components/ai/snapshot-detail-client";

export default async function SnapshotDetailPage(props: PageProps<"/ai/[id]">) {
  const { id } = await props.params;
  return <SnapshotDetailClient id={id} />;
}
