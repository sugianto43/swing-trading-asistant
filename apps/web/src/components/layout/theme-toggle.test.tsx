import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider } from "next-themes";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ThemeToggle } from "./theme-toggle";

function renderToggle() {
  return render(
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <ThemeToggle />
    </ThemeProvider>,
  );
}

describe("ThemeToggle", () => {
  it("toggles the document's dark class when clicked", async () => {
    const user = userEvent.setup();
    renderToggle();

    const button = await screen.findByRole("button", { name: "Toggle theme" });
    await waitFor(() => expect(button).not.toBeDisabled());

    expect(document.documentElement.classList.contains("dark")).toBe(false);

    await user.click(button);

    await waitFor(() => expect(document.documentElement.classList.contains("dark")).toBe(true));
  });

  it("toggles back from dark to light on a second click", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
        <ThemeToggle />
      </ThemeProvider>,
    );

    const button = await screen.findByRole("button", { name: "Toggle theme" });
    await waitFor(() => expect(button).not.toBeDisabled());
    await waitFor(() => expect(document.documentElement.classList.contains("dark")).toBe(true));

    await user.click(button);

    await waitFor(() => expect(document.documentElement.classList.contains("dark")).toBe(false));
  });

  it("renders disabled on the server, matching the client's pre-hydration pass", () => {
    // Regression test for a real hydration mismatch this component
    // shipped with: resolvedTheme resolves synchronously on the
    // client's first render (from localStorage/matchMedia), so it's
    // NEVER undefined in the browser — only during SSR. A component
    // that gates on "resolvedTheme === undefined" therefore never
    // renders its placeholder on the client, only on the server,
    // guaranteeing a server/client mismatch. useHasMounted must render
    // `false` here (server) so the disabled placeholder — not the real
    // toggle — is what SSR actually emits.
    const html = renderToStaticMarkup(
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
        <ThemeToggle />
      </ThemeProvider>,
    );
    expect(html).toContain("disabled");
  });
});
