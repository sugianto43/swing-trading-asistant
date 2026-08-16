import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

const upsertJournal = vi.fn();
vi.mock("@/lib/queries/positions", () => ({
  upsertJournal: (positionId: string, payload: unknown) => upsertJournal(positionId, payload),
}));

import { JournalForm } from "./journal-form";
import type { Journal } from "@/lib/queries/positions";

function renderForm(journal: Journal | null) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <JournalForm positionId="pos-1" journal={journal} />
    </QueryClientProvider>,
  );
}

describe("JournalForm", () => {
  it("renders an empty form when no journal exists yet", () => {
    renderForm(null);

    expect(screen.getByLabelText("Thesis")).toHaveValue("");
  });

  it("prefills fields from an existing journal entry", () => {
    renderForm({
      id: "j1",
      position_id: "pos-1",
      thesis: "breakout continuation",
      market_context: null,
      execution_quality: null,
      behavioral_notes: null,
      plan_adherence_notes: null,
      mistakes: null,
      lessons: null,
      reference_urls: ["https://example.com/chart"],
      created_at: "2024-03-01T00:00:00Z",
      updated_at: "2024-03-01T00:00:00Z",
    });

    expect(screen.getByLabelText("Thesis")).toHaveValue("breakout continuation");
    expect(screen.getByDisplayValue("https://example.com/chart")).toBeInTheDocument();
  });

  it("submits the entered fields on save", async () => {
    const user = userEvent.setup();
    upsertJournal.mockResolvedValueOnce({ id: "j1", position_id: "pos-1" });
    renderForm(null);

    await user.type(screen.getByLabelText("Thesis"), "breakout continuation");
    await user.click(screen.getByRole("button", { name: "Save journal entry" }));

    await waitFor(() =>
      expect(upsertJournal).toHaveBeenCalledWith(
        "pos-1",
        expect.objectContaining({ thesis: "breakout continuation" }),
      ),
    );
    await waitFor(() => expect(screen.getByText("Journal entry saved.")).toBeInTheDocument());
  });

  it("adds and removes reference URL rows", async () => {
    const user = userEvent.setup();
    renderForm(null);

    expect(screen.queryByPlaceholderText("https://…")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Add URL" }));
    expect(screen.getByPlaceholderText("https://…")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Remove" }));
    expect(screen.queryByPlaceholderText("https://…")).not.toBeInTheDocument();
  });

  it("shows a validation error and never submits when a reference URL row is left blank", async () => {
    const user = userEvent.setup();
    renderForm(null);

    await user.click(screen.getByRole("button", { name: "Add URL" }));
    await user.click(screen.getByRole("button", { name: "Save journal entry" }));

    await waitFor(() => expect(screen.getByText("Required")).toBeInTheDocument());
    expect(upsertJournal).not.toHaveBeenCalled();
  });

  it("omits blank optional fields as undefined rather than sending empty strings", async () => {
    const user = userEvent.setup();
    upsertJournal.mockResolvedValueOnce({ id: "j1", position_id: "pos-1" });
    renderForm(null);

    await user.click(screen.getByRole("button", { name: "Save journal entry" }));

    await waitFor(() =>
      expect(upsertJournal).toHaveBeenCalledWith(
        "pos-1",
        expect.objectContaining({
          thesis: undefined,
          market_context: undefined,
          execution_quality: undefined,
          behavioral_notes: undefined,
          plan_adherence_notes: undefined,
          mistakes: undefined,
          lessons: undefined,
          reference_urls: [],
        }),
      ),
    );
  });

  it("shows a distinct error when the save fails", async () => {
    const user = userEvent.setup();
    upsertJournal.mockRejectedValueOnce(new Error("network down"));
    renderForm(null);

    await user.click(screen.getByRole("button", { name: "Save journal entry" }));

    await waitFor(() =>
      expect(screen.getByText("Couldn't save journal entry. Check that the API is reachable and retry.")).toBeInTheDocument(),
    );
  });
});
