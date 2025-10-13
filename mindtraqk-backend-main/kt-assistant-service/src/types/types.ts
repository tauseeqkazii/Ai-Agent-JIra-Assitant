import { ObjectId } from "mongodb"; // or from "mongoose" if using Mongoose

export interface LoginToken {
  id: string;
  Role: string;

  address: {
    street: string;
    city: string;
    state: string;
    country: string;
    zipCode: string;
  };

  currentAddress: {
    street: string;
    city: string;
    state: string;
    country: string;
    zipCode: string;
  };

  _id: ObjectId;
  firstName: string;
  lastName: string;
  email: string;
  employeeId: string;
  department: string;
  designation: string;
  status: "ACTIVE" | "INACTIVE" | "PENDING";

  teamMembers: ObjectId[];
  Tenant: ObjectId;
  role: string;

  createdAt: Date;
  updatedAt: Date;
  __v: number;

  reportingTo: ObjectId;

  skills: string[];
  altContactNumber: string;
  contactNumber: string;
  dateOfBirth: Date;
  gender: "MALE" | "FEMALE" | "OTHER";
}
