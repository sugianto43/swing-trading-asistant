"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useFieldArray, useForm } from "react-hook-form";
import { z } from "zod";

import { TradePlanResult } from "@/components/risk/trade-plan-result";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { createTradePlan, type TradePlan } from "@/lib/queries/risk";
import { SETUP_TYPES, type SetupType } from "@/lib/queries/setup-types";

const positionSchema = z.object({
  symbol: z.string().min(1, "Required"),
  sector: z.string().optional(),
  allocation_amount: z.coerce.number().positive("Must be positive"),
});

const formSchema = z.object({
  symbol: z.string().min(1, "Symbol is required"),
  setup_type: z.enum(SETUP_TYPES as [SetupType, ...SetupType[]], {
    message: "Setup type is required",
  }),
  plan_date: z.string().min(1, "Plan date is required"),
  capital: z.coerce.number().positive("Capital must be a positive number"),
  existing_positions: z.array(positionSchema),
});

// z.coerce.number() makes the schema's INPUT type (what the form fields
// hold before validation, e.g. a string from an <input>) differ from its
// OUTPUT type (what handleSubmit's callback actually receives, coerced
// to number) — react-hook-form's useForm generic must be the input type,
// or TS rejects the resolver/register calls with a type mismatch that
// has nothing to do with real form behavior.
export type TradePlanFormInput = z.input<typeof formSchema>;
export type TradePlanFormValues = z.output<typeof formSchema>;

export function TradePlanForm({
  defaultSymbol,
  defaultSetupType,
  defaultPlanDate,
}: {
  defaultSymbol?: string;
  defaultSetupType?: SetupType;
  defaultPlanDate?: string;
}) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    control,
    setValue,
    formState: { errors },
  } = useForm<TradePlanFormInput, unknown, TradePlanFormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      symbol: defaultSymbol ?? "",
      setup_type: defaultSetupType,
      plan_date: defaultPlanDate ?? new Date().toISOString().slice(0, 10),
      capital: undefined,
      existing_positions: [],
    },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "existing_positions" });

  const mutation = useMutation<TradePlan, Error, TradePlanFormValues>({
    mutationFn: (values) =>
      createTradePlan({
        symbol: values.symbol.toUpperCase(),
        setup_type: values.setup_type,
        plan_date: values.plan_date,
        capital: values.capital,
        existing_positions: values.existing_positions,
      }),
    onSuccess: () => {
      // A VALID or REJECTED result both change what the list below shows
      // (upsert-by-natural-key means this may update an existing row).
      queryClient.invalidateQueries({ queryKey: ["trade-plans"] });
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
            <Label htmlFor="setup_type">Setup type</Label>
            <Select
              defaultValue={defaultSetupType}
              onValueChange={(value) => {
                // react-hook-form's register doesn't cover Radix Select
                // directly; wire it via the field's onChange from
                // register's returned ref is awkward here, so a plain
                // controlled onValueChange calling setValue is used
                // instead for this one field.
                setValue("setup_type", value as SetupType, { shouldValidate: true });
              }}
            >
              <SelectTrigger id="setup_type" aria-label="Setup type" className="w-full">
                <SelectValue placeholder="Select a setup" />
              </SelectTrigger>
              <SelectContent>
                {SETUP_TYPES.map((setup) => (
                  <SelectItem key={setup} value={setup}>
                    {setup}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.setup_type && (
              <p className="text-xs text-destructive">{errors.setup_type.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="plan_date">Plan date</Label>
            <Input id="plan_date" type="date" {...register("plan_date")} />
            {errors.plan_date && (
              <p className="text-xs text-destructive">{errors.plan_date.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="capital">Capital (IDR)</Label>
            <Input id="capital" type="number" {...register("capital")} />
            {errors.capital && <p className="text-xs text-destructive">{errors.capital.message}</p>}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <Label>Existing positions (optional)</Label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => append({ symbol: "", sector: "", allocation_amount: 0 })}
            >
              Add position
            </Button>
          </div>
          {fields.map((field, index) => (
            <div key={field.id} className="flex items-center gap-2">
              <Input
                placeholder="Symbol"
                className="w-32"
                {...register(`existing_positions.${index}.symbol`)}
              />
              <Input
                placeholder="Sector (optional)"
                className="w-40"
                {...register(`existing_positions.${index}.sector`)}
              />
              <Input
                placeholder="Allocation amount"
                type="number"
                className="w-40"
                {...register(`existing_positions.${index}.allocation_amount`)}
              />
              <Button type="button" variant="ghost" size="sm" onClick={() => remove(index)}>
                Remove
              </Button>
            </div>
          ))}
        </div>

        <Button type="submit" disabled={mutation.isPending} className="self-start">
          {mutation.isPending ? "Building plan…" : "Build trade plan"}
        </Button>
      </form>

      {mutation.isError && (
        <p className="text-sm text-destructive">
          Couldn&apos;t build the trade plan. Check that the API is reachable and retry.
        </p>
      )}
      {mutation.isSuccess && mutation.variables && (
        <TradePlanResult plan={mutation.data} symbol={mutation.variables.symbol.toUpperCase()} />
      )}
    </div>
  );
}
