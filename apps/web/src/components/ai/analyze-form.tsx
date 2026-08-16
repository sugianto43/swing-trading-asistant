"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AnalysisResult } from "@/components/ai/analysis-result";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { analyzeQuestion, type AnalysisSnapshot } from "@/lib/queries/ai";

const MAX_QUESTION_LENGTH = 4000;

const formSchema = z.object({
  question: z
    .string()
    .min(1, "Question is required")
    .max(MAX_QUESTION_LENGTH, `Question must be ${MAX_QUESTION_LENGTH} characters or fewer`),
  symbol: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

export function AnalyzeForm({ defaultSymbol }: { defaultSymbol?: string }) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { question: "", symbol: defaultSymbol ?? "" },
  });

  const mutation = useMutation<AnalysisSnapshot, Error, FormValues>({
    mutationFn: (values) =>
      analyzeQuestion({
        question: values.question,
        symbol: values.symbol ? values.symbol.toUpperCase() : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-snapshots"] });
    },
  });

  return (
    <div className="flex flex-col gap-4">
      <form
        onSubmit={handleSubmit((values) => mutation.mutate(values))}
        className="flex flex-col gap-4 rounded-lg border border-border p-4"
      >
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="question">Question</Label>
          <Textarea id="question" rows={3} {...register("question")} />
          {errors.question && <p className="text-xs text-destructive">{errors.question.message}</p>}
        </div>

        <div className="flex flex-col gap-1.5 sm:w-48">
          <Label htmlFor="symbol">Symbol (optional)</Label>
          <Input id="symbol" {...register("symbol")} />
        </div>

        <Button type="submit" disabled={mutation.isPending} className="self-start">
          {mutation.isPending ? "Analyzing…" : "Ask"}
        </Button>
      </form>

      {mutation.isError && (
        <p className="text-sm text-destructive">{mutation.error.message}</p>
      )}
      {mutation.isSuccess && <AnalysisResult snapshot={mutation.data} />}
    </div>
  );
}
