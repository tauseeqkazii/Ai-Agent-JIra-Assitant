// utils/wrapAsyncMiddleware.ts
import { Request, Response, NextFunction, RequestHandler } from "express";

export function wrapAsyncMiddleware(
  fn: (req: Request, res: Response, next: NextFunction) => Promise<void>
): RequestHandler {
  return (req, res, next) => {
    fn(req, res, next).catch(next);
  };
}
