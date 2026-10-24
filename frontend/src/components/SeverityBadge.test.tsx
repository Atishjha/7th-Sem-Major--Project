import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { SeverityBadge } from "@/components/SeverityBadge";

describe("SeverityBadge", () => {
  it.each(["low", "medium", "high", "critical"] as const)("shows %s", (s) => {
    render(<SeverityBadge severity={s} />);
    expect(screen.getByText(s)).toBeInTheDocument();
  });
});
