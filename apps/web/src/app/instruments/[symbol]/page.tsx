import { InstrumentDetailClient } from "@/components/instrument/detail-client";

export default async function InstrumentDetailPage(props: PageProps<"/instruments/[symbol]">) {
  const { symbol } = await props.params;
  return <InstrumentDetailClient symbol={symbol} />;
}
