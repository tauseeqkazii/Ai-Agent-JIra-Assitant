// models/JiraUpdateLog.ts
import { Schema, model, Document } from "mongoose";

export interface IJiraUpdateLog extends Document {
  userId: string;
  taskId: string;
  summary: string;
  updatedAt: Date;
}

const JiraUpdateLogSchema = new Schema<IJiraUpdateLog>(
  {
    userId: { type: String, required: true },
    taskId: { type: String, required: true },
    summary: { type: String, required: true },
  },
  { timestamps: { createdAt: false, updatedAt: true } }
);

export const JiraUpdateLog = model<IJiraUpdateLog>(
  "JiraUpdateLog",
  JiraUpdateLogSchema
);
