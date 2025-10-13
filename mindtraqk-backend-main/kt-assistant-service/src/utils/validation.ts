import { z } from "zod";
import { KTPriority } from "./enum";

export const assistantResValidation = z.object({
  prompt: z
    .string({
      required_error: "Prompt is required",
      invalid_type_error: "Prompt must be a string",
    })
    .min(1, "Prompt cannot be empty"),
});

export const ktAlertValidation = z.object({
  title: z
    .string({
      required_error: "Title is required",
      invalid_type_error: "Title must be a string",
    })
    .min(1, "Title cannot be empty"),

  description: z
    .string({
      required_error: "Description is required",
      invalid_type_error: "Description must be a string",
    })
    .min(1, "Description cannot be empty"),
  productArea: z
    .string({
      required_error: "Product Area is required",
      invalid_type_error: "Product Area must be a string",
    })
    .min(1, "Product Area cannot be empty"),
  priority: z.enum(
    [KTPriority.Low, KTPriority.Medium, KTPriority.High, KTPriority.Critical],
    {
      required_error: "Priority is required",
    }
  ),
});
