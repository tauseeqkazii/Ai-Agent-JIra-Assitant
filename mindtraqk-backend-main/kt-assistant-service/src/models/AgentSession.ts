import { Schema, model, Document } from "mongoose";
import { AgentTaskState } from "../utils/enum";

export interface ITaskState {
  taskId: string;
  title: string;
  status: string;
  pendingStatusDone?: boolean;
  createdAt?: Date;
  updatedAt?: Date;
  draftSummary?: string;
  finalSummary?: string;
  state: AgentTaskState;
}

export interface IAgentSession extends Document {
  userId: string;
  currentIndex: number;
  tasks: ITaskState[];
  createdAt: Date;
  updatedAt: Date;
}

const TaskStateSchema = new Schema<ITaskState>(
  {
    taskId: { type: String, required: true },
    title: { type: String, required: true },
    status: { type: String, required: true },
    createdAt: { type: Date },
    updatedAt: { type: Date },
    draftSummary: { type: String },
    finalSummary: { type: String },
    state: {
      type: String,
      enum: Object.values(AgentTaskState),
      default: AgentTaskState.AWAITING_UPDATE,
    },
  },
  { _id: false }
);

const AgentSessionSchema = new Schema<IAgentSession>(
  {
    userId: { type: String, required: true },
    currentIndex: { type: Number, default: 0 },
    tasks: { type: [TaskStateSchema], required: true },
  },
  { timestamps: true }
);

export const AgentSession = model<IAgentSession>(
  "AgentSession",
  AgentSessionSchema
);
