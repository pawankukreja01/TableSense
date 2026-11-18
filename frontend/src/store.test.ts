import { describe, it, expect } from "vitest";
import { money } from "./store";
describe("displayed prices", () => {
  it("keeps pence exact", () => {
    expect(money(450)).toBe("£4.50");
    expect(money(325)).toBe("£3.25");
  });
});
