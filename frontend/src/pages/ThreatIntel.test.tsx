import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import ThreatIntel from "@/pages/ThreatIntel";

describe("ThreatIntel page", () => {
  it("states plainly that no external feeds are queried", () => {
    render(<ThreatIntel />);
    expect(screen.getByText("Not part of this project")).toBeInTheDocument();
    expect(screen.getByText(/does not query external threat-intelligence feeds/)).toBeInTheDocument();
  });
});
