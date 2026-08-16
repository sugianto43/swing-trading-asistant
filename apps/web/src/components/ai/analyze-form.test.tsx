import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

const analyzeQuestion = vi.fn();
vi.mock("@/lib/queries/ai", () => ({
  analyzeQuestion: (payload: unknown) => analyzeQuestion(payload),
}));

import { AnalyzeForm } from "./analyze-form";

function renderForm(props: React.ComponentProps<typeof AnalyzeForm> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(
    <QueryClientProvider client={queryClient}>
      <AnalyzeForm {...props} />
    </QueryClientProvider>,
  );
  return { ...view, queryClient };
}

const SNAPSHOT = {
  id: "1",
  instrument_id: null,
  provider: "gemini",
  model: "gemini-2.0-flash",
  prompt_version: "v1",
  question: "What is BBCA's setup?",
  tool_calls: [],
  structured_data_snapshot: [],
  response: "BBCA shows a breakout setup.",
  guardrail_flags: [],
  created_at: "2024-03-01T00:00:00Z",
};

describe("AnalyzeForm", () => {
  it("prefills the symbol from props", () => {
    renderForm({ defaultSymbol: "BBCA" });

    expect(screen.getByLabelText("Symbol (optional)")).toHaveValue("BBCA");
  });

  it("shows a validation error and never submits when the question is blank", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(screen.getByText("Question is required")).toBeInTheDocument());
    expect(analyzeQuestion).not.toHaveBeenCalled();
  });

  it("rejects a question over the 4000-character limit", async () => {
    const user = userEvent.setup();
    renderForm();

    // Direct paste avoids userEvent.type's per-character cost for 4001 chars.
    await user.click(screen.getByLabelText("Question"));
    await user.paste("a".repeat(4001));
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() =>
      expect(screen.getByText("Question must be 4000 characters or fewer")).toBeInTheDocument(),
    );
    expect(analyzeQuestion).not.toHaveBeenCalled();
  });

  it("accepts a question at exactly the 4000-character boundary", async () => {
    const user = userEvent.setup();
    analyzeQuestion.mockResolvedValueOnce(SNAPSHOT);
    renderForm();

    await user.click(screen.getByLabelText("Question"));
    await user.paste("a".repeat(4000));
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(analyzeQuestion).toHaveBeenCalled());
    expect(
      screen.queryByText("Question must be 4000 characters or fewer"),
    ).not.toBeInTheDocument();
  });

  it("renders the response on success", async () => {
    const user = userEvent.setup();
    analyzeQuestion.mockResolvedValueOnce(SNAPSHOT);
    renderForm();

    await user.type(screen.getByLabelText("Question"), "What is BBCA's setup?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(screen.getByText("BBCA shows a breakout setup.")).toBeInTheDocument());
  });

  it("invalidates the ai-snapshots list so Recent Analyses reflects the new question, on success", async () => {
    const user = userEvent.setup();
    analyzeQuestion.mockResolvedValueOnce(SNAPSHOT);
    const { queryClient } = renderForm();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    await user.type(screen.getByLabelText("Question"), "What is BBCA's setup?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["ai-snapshots"] }),
    );
  });

  it("uppercases the symbol before submitting", async () => {
    const user = userEvent.setup();
    analyzeQuestion.mockResolvedValueOnce(SNAPSHOT);
    renderForm();

    await user.type(screen.getByLabelText("Question"), "What is BBCA's setup?");
    await user.type(screen.getByLabelText("Symbol (optional)"), "bbca");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() =>
      expect(analyzeQuestion).toHaveBeenCalledWith(expect.objectContaining({ symbol: "BBCA" })),
    );
  });

  it("omits the symbol entirely when left blank", async () => {
    const user = userEvent.setup();
    analyzeQuestion.mockResolvedValueOnce(SNAPSHOT);
    renderForm();

    await user.type(screen.getByLabelText("Question"), "What is BBCA's setup?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(analyzeQuestion).toHaveBeenCalled());
    expect(analyzeQuestion.mock.calls[0][0].symbol).toBeUndefined();
  });

  it("renders the backend's exact message plainly when no provider is configured (503), not a generic error", async () => {
    const user = userEvent.setup();
    analyzeQuestion.mockRejectedValueOnce(
      new Error("no LLM provider configured — set GEMINI_API_KEY, or pass an explicit provider"),
    );
    renderForm();

    await user.type(screen.getByLabelText("Question"), "What is BBCA's setup?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() =>
      expect(
        screen.getByText(
          "no LLM provider configured — set GEMINI_API_KEY, or pass an explicit provider",
        ),
      ).toBeInTheDocument(),
    );
  });
});
