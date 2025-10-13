import httpStatus from "http-status";
import ApiResponse from "../utils/apiResponse";
import { Request, Response, NextFunction } from "express";

export const allowedTo = (...roles: string[]) => {
  return (req: Request, res: Response, next: NextFunction): void => {
    if (!roles.includes(req.body.user.role)) {
      ApiResponse.forbidden(
        res,
        "You do not have permission to perform this action."
      );
      return; // ✅ return void
    }

    next(); // ✅ allowed
  };
};
