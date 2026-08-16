"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useFieldArray, useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { upsertJournal, type Journal } from "@/lib/queries/positions";

const formSchema = z.object({
  thesis: z.string().optional(),
  market_context: z.string().optional(),
  execution_quality: z.string().optional(),
  behavioral_notes: z.string().optional(),
  plan_adherence_notes: z.string().optional(),
  mistakes: z.string().optional(),
  lessons: z.string().optional(),
  reference_urls: z.array(z.object({ value: z.string().min(1, "Required") })),
});

type FormValues = z.infer<typeof formSchema>;

export function JournalForm({ positionId, journal }: { positionId: string; journal: Journal | null }) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      thesis: journal?.thesis ?? "",
      market_context: journal?.market_context ?? "",
      execution_quality: journal?.execution_quality ?? "",
      behavioral_notes: journal?.behavioral_notes ?? "",
      plan_adherence_notes: journal?.plan_adherence_notes ?? "",
      mistakes: journal?.mistakes ?? "",
      lessons: journal?.lessons ?? "",
      reference_urls: (journal?.reference_urls ?? []).map((value) => ({ value })),
    },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "reference_urls" });

  const mutation = useMutation<Journal, Error, FormValues>({
    mutationFn: (values) =>
      upsertJournal(positionId, {
        thesis: values.thesis || undefined,
        market_context: values.market_context || undefined,
        execution_quality: values.execution_quality || undefined,
        behavioral_notes: values.behavioral_notes || undefined,
        plan_adherence_notes: values.plan_adherence_notes || undefined,
        mistakes: values.mistakes || undefined,
        lessons: values.lessons || undefined,
        reference_urls: values.reference_urls.map((r) => r.value),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["journal", positionId] });
    },
  });

  return (
    <form
      onSubmit={handleSubmit((values) => mutation.mutate(values))}
      className="flex flex-col gap-4 rounded-lg border border-border p-4"
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="thesis">Thesis</Label>
          <Textarea id="thesis" {...register("thesis")} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="market_context">Market context</Label>
          <Textarea id="market_context" {...register("market_context")} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="execution_quality">Execution quality</Label>
          <Textarea id="execution_quality" {...register("execution_quality")} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="behavioral_notes">Behavioral notes</Label>
          <Textarea id="behavioral_notes" {...register("behavioral_notes")} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="plan_adherence_notes">Plan adherence notes</Label>
          <Textarea id="plan_adherence_notes" {...register("plan_adherence_notes")} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="mistakes">Mistakes</Label>
          <Textarea id="mistakes" {...register("mistakes")} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="lessons">Lessons</Label>
          <Textarea id="lessons" {...register("lessons")} />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <Label>Reference URLs (optional)</Label>
          <Button type="button" variant="outline" size="sm" onClick={() => append({ value: "" })}>
            Add URL
          </Button>
        </div>
        {fields.map((field, index) => (
          <div key={field.id} className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <Input placeholder="https://…" {...register(`reference_urls.${index}.value`)} />
              <Button type="button" variant="ghost" size="sm" onClick={() => remove(index)}>
                Remove
              </Button>
            </div>
            {errors.reference_urls?.[index]?.value && (
              <p className="text-xs text-destructive">
                {errors.reference_urls[index]?.value?.message}
              </p>
            )}
          </div>
        ))}
      </div>

      <Button type="submit" disabled={mutation.isPending} className="self-start">
        {mutation.isPending ? "Saving…" : "Save journal entry"}
      </Button>
      {mutation.isError && (
        <p className="text-sm text-destructive">Couldn&apos;t save journal entry. Check that the API is reachable and retry.</p>
      )}
      {mutation.isSuccess && <p className="text-sm text-muted-foreground">Journal entry saved.</p>}
    </form>
  );
}
