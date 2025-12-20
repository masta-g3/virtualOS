import { describe, it, expect } from "vitest";
import { createModel, MODEL_KEYS } from "../src/models.js";

describe("models", () => {
  it.each(MODEL_KEYS)("createModel('%s') returns valid model", (key) => {
    const { model } = createModel(key);
    expect(model).toBeDefined();
    expect(model.modelId).toBeTruthy();
  });
});
