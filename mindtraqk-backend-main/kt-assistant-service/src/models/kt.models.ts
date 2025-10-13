import { Schema, model, Document, Types } from "mongoose";
import { KTPriority, KTStatus } from "../utils/enum";

export interface IKTAlert extends Document {
  user: Types.ObjectId;
  title: string;
  description: string;
  productArea: string;
  priority: KTPriority;
  status: KTStatus;
  request_date: Date;
  reporting_manager: Types.ObjectId;
  assigned_to?: {
    name: string;
  };
  is_acknowledged: boolean;
}

const KTAlertSchema = new Schema<IKTAlert>(
  {
    user: {
      type: Schema.Types.ObjectId,
      ref: "mindituser",
      // required: true,
    },
    title: { type: String, required: true },
    description: { type: String, required: true },
    productArea: { type: String, required: true },
    priority: {
      type: String,
      enum: Object.values(KTPriority),
      default: KTPriority.Low,
    },
    status: {
      type: String,
      enum: Object.values(KTStatus),
      default: KTStatus.Pending,
    },
    request_date: { type: Date, default: Date.now },

    reporting_manager: {
      type: Schema.Types.ObjectId,
      ref: "mindituser",
    },

    assigned_to: {
      type: Schema.Types.ObjectId,
      ref: "mindituser",
    },

    is_acknowledged: { type: Boolean, default: false },
  },
  {
    timestamps: true,
  }
);

export const KTModel = model<IKTAlert>("KTAlert", KTAlertSchema);
