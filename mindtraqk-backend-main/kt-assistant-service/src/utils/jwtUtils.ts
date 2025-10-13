import jwt from "jsonwebtoken";
import { NextFunction, Request, Response } from "express";
import ResponseHandler from "./apiResponse";
import { UserModel } from "../models/User.model";
// import User from "../models/UserM.model";

class JWTUtils {
  generateToken(payload: object) {
    return jwt.sign(payload, process.env.JWT_SECRET as string);
  }

  jwtMiddleware(req: Request, res: Response, next: NextFunction): void {
    const token = req.cookies["mindtraqk-token"];
    console.log("token", token);
    if (!token) {
      res.status(401).json({ message: "Unauthorized" });
      return;
    }

    try {
      const decoded = jwt.verify(token, process.env.JWT_SECRET!) as {
        id: string;
      };
      UserModel.findById(decoded.id)
        .select("-password")
        .then((user) => {
          if (!user) {
            res.status(401).json({ message: "User not found" });
            return;
          }
          req.body.user = user;
          console.log("in jwt middleware", req.body.user.role);
          next();
        })
        .catch((err) => {
          console.error("DB error", err);
          res.status(500).json({ message: "Internal server error" });
        });
    } catch (err) {
      res.status(401).json({ message: "Invalid token" });
    }
  }
}

export default new JWTUtils();
