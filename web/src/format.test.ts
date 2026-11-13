import { describe, expect, it } from "vitest";
import { formatRate, formatTemp } from "./format";

describe("formatters", () => {
  it("renders rates and temperatures", () => {
    expect(formatRate(0.525)).toBe("52.5%");
    expect(formatRate(null)).toBe("n/a");
    expect(formatTemp(54.2)).toBe("54.20 C");
    expect(formatTemp(null)).toBe("n/a");
  });
});
