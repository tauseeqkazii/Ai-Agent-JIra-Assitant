import { Document, Schema, model, Types } from "mongoose";

export interface IUser extends Document {
  firstName: string;
  lastName: string;
  email: string;
  dateOfBirth?: Date;
  joiningDate?: Date;
  phoneNo?: string;
  employeeId: string;
  role: string;
  designation: string;
  teamMembers?: Types.ObjectId[];
  reportingTo?: Types.ObjectId;
  Tenant: Types.ObjectId;
  address?: {
    street: string;
    city: string;
    state: string;
    country: string;
    zipCode: string;
  };
  contactNumber?: string;
  altContactNumber?: string;
  currentAddress?: {
    street: string;
    city: string;
    state: string;
    country: string;
    zipCode: string;
  };
  skills?: string[];
  createdAt: Date;
  updatedAt: Date;
}

const UserSchema = new Schema<IUser>(
  {
    firstName: { type: String, required: true },
    lastName: { type: String, required: true },
    email: { type: String, required: true },
    dateOfBirth: { type: Date },
    joiningDate: { type: Date },
    phoneNo: { type: String },
    employeeId: { type: String, required: true },

    designation: { type: String, required: true },

    teamMembers: [
      {
        type: Schema.Types.ObjectId,
        ref: "mindituser",
      },
    ],
    reportingTo: {
      type: Schema.Types.ObjectId,
      ref: "mindituser",
    },
    Tenant: {
      type: Schema.Types.ObjectId,
      ref: "Tenant",
      required: true,
    },
    address: {
      street: { type: String, required: true },
      city: { type: String, required: true },
      state: { type: String, required: true },
      country: { type: String, required: true },
      zipCode: { type: String, required: true },
    },

    contactNumber: { type: String }, // ← added
    role: { type: String }, // ← added
    altContactNumber: { type: String }, // ← added
    currentAddress: {
      street: { type: String, required: false },
      city: { type: String, required: false },
      state: { type: String, required: false },
      country: { type: String, required: false },
      zipCode: { type: String, required: false },
    },
    skills: {
      type: [String],
      default: [],
    },
  },
  { timestamps: true }
);

export const UserModel = model<IUser>("mindituser", UserSchema);
