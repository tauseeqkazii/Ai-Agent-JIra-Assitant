import { Schema, model, Document, Types } from "mongoose";
import { Platforms } from "../utils/enum";

export interface IIntegrationToken extends Document {
  userId: string;
  user: Types.ObjectId;
  platform: Platforms;
  accessToken: string;
  refreshToken?: string;
  expiresAt?: Date;
  WorkspaceDetails?: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
  profileData?: Record<string, any>;
}

const integrationTokenSchema = new Schema<IIntegrationToken>(
  {
    userId: {
      type: String,
      required: true,
    },
    user: {
      type: Schema.Types.ObjectId,
      ref: "mindituser",
      // required: true,
    },
    platform: {
      type: String,
      enum: Object.values(Platforms),
      required: true,
    },
    accessToken: {
      type: String,
      required: true,
    },
    refreshToken: {
      type: String,
      required: false,
    },
    expiresAt: {
      type: Date,
      required: false,
    },
    profileData: {
      type: Schema.Types.Mixed,
      required: false,
    },
    WorkspaceDetails: {
      type: Schema.Types.Mixed,
      required: false,
    },
  },
  {
    timestamps: true,
  }
);

const IntegrationToken = model<IIntegrationToken>(
  "IntegrationToken",
  integrationTokenSchema
);
export default IntegrationToken;
