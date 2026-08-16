"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ExecutionResult } from "@/components/positions/execution-result";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { recordExecution, type ExecutionSide, type Position } from "@/lib/queries/positions";

const SIDES: ExecutionSide[] = ["BUY", "SELL"];

const formSchema = z.object({
  symbol: z.string().min(1, "Symbol is required"),
  side: z.enum(SIDES as [ExecutionSide, ...ExecutionSide[]], { message: "Side is required" }),
  quantity: z.coerce.number().positive("Quantity must be a positive number"),
  price: z.coerce.number().positive("Price must be a positive number"),
  fee: z.coerce.number().min(0, "Fee cannot be negative"),
  executed_at: z.string().min(1, "Execution time is required"),
  trade_plan_id: z.string().optional(),
  notes: z.string().optional(),
});

export type ExecutionFormInput = z.input<typeof formSchema>;
export type ExecutionFormValues = z.output<typeof formSchema>;

function toIso(localDateTime: string): string {
  // The <input type="datetime-local"> value has no timezone offset — the
  // browser treats it as local time. new Date(...) on that string is
  // parsed as local time too, so .toISOString() converts it to the UTC
  // instant the user actually meant (MASTER-TDD: UTC storage, explicit
  // market-local conversion), rather than storing the naive local digits
  // as if they were already UTC.
  return new Date(localDateTime).toISOString();
}

export function ExecutionForm({
  defaultSymbol,
  defaultTradePlanId,
}: {
  defaultSymbol?: string;
  defaultTradePlanId?: string;
}) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<ExecutionFormInput, unknown, ExecutionFormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      symbol: defaultSymbol ?? "",
      side: undefined,
      quantity: undefined,
      price: undefined,
      fee: 0,
      executed_at: "",
      trade_plan_id: defaultTradePlanId ?? "",
      notes: "",
    },
  });

  const mutation = useMutation<Position, Error, ExecutionFormValues>({
    mutationFn: (values) =>
      recordExecution({
        symbol: values.symbol.toUpperCase(),
        side: values.side,
        quantity: values.quantity,
        price: values.price,
        fee: values.fee,
        executed_at: toIso(values.executed_at),
        trade_plan_id: values.trade_plan_id || undefined,
        notes: values.notes || undefined,
      }),
    onSuccess: (data) => {
      // A follow-up execution against an already-open position (e.g.
      // adding to it or a partial exit) updates that position's own
      // record too, not just its place in the list — invalidate its
      // detail/execution-history caches directly, or a currently-mounted
      // (or recently-cached) detail page shows pre-execution numbers for
      // up to the app's staleTime.
      queryClient.invalidateQueries({ queryKey: ["positions"] });
      queryClient.invalidateQueries({ queryKey: ["position", data.id] });
      queryClient.invalidateQueries({ queryKey: ["executions", data.id] });
    },
  });

  return (
    <div className="flex flex-col gap-4">
      <form
        onSubmit={handleSubmit((values) => mutation.mutate(values))}
        className="flex flex-col gap-4 rounded-lg border border-border p-4"
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="symbol">Symbol</Label>
            <Input id="symbol" {...register("symbol")} />
            {errors.symbol && <p className="text-xs text-destructive">{errors.symbol.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="side">Side</Label>
            <Select onValueChange={(value) => setValue("side", value as ExecutionSide, { shouldValidate: true })}>
              <SelectTrigger id="side" aria-label="Side" className="w-full">
                <SelectValue placeholder="Select a side" />
              </SelectTrigger>
              <SelectContent>
                {SIDES.map((side) => (
                  <SelectItem key={side} value={side}>
                    {side}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.side && <p className="text-xs text-destructive">{errors.side.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="quantity">Quantity</Label>
            <Input id="quantity" type="number" {...register("quantity")} />
            {errors.quantity && <p className="text-xs text-destructive">{errors.quantity.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="price">Price (IDR)</Label>
            <Input id="price" type="number" {...register("price")} />
            {errors.price && <p className="text-xs text-destructive">{errors.price.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="fee">Fee (IDR)</Label>
            <Input id="fee" type="number" {...register("fee")} />
            {errors.fee && <p className="text-xs text-destructive">{errors.fee.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="executed_at">Executed at</Label>
            <Input id="executed_at" type="datetime-local" {...register("executed_at")} />
            {errors.executed_at && (
              <p className="text-xs text-destructive">{errors.executed_at.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="notes">Notes (optional)</Label>
            <Input id="notes" {...register("notes")} />
          </div>
        </div>

        <Button type="submit" disabled={mutation.isPending} className="self-start">
          {mutation.isPending ? "Recording…" : "Record execution"}
        </Button>
      </form>

      {mutation.isError && (
        <p className="text-sm text-destructive">Couldn&apos;t record execution: {mutation.error.message}</p>
      )}
      {mutation.isSuccess && mutation.variables && (
        <ExecutionResult position={mutation.data} symbol={mutation.variables.symbol.toUpperCase()} />
      )}
    </div>
  );
}
