export function StubPage({ title, phase }: { title: string; phase: number }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center">
      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      <p className="text-muted-foreground">Coming in Phase {phase}.</p>
    </div>
  );
}
