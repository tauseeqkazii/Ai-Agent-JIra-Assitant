import { NextFunction, Request, Response } from "express";
import catchAsync from "../utils/catchAsync";
import { ktAlertValidation } from "../utils/validation";
import KTService from "../services/KT.service";
import { LoginToken } from "../types/types";

class KTController {
  // Create KT Alert
  create = catchAsync(
    async (req: Request, res: Response, next: NextFunction) => {
      const result = ktAlertValidation.parse(req.body);
      await KTService.create(result, res, req.body.user);
    }
  );

  // Get All KT Alerts with filtering, search, pagination
  getAll = catchAsync(
    async (req: Request, res: Response, next: NextFunction) => {
      await KTService.getAll(req, res);
    }
  );

  // ✅ Manager: Get KT alerts for team members
  getManagerAlerts = catchAsync(
    async (req: Request, res: Response, next: NextFunction) => {
      const userData: LoginToken = req.body.user;
      await KTService.getByManager(req, res, userData);
    }
  );

  // ✅ Employee: Get own KT alerts
  getEmployeeAlerts = catchAsync(
    async (req: Request, res: Response, next: NextFunction) => {
      const userData: LoginToken = req.body.user;
      await KTService.getByEmployee(req, res, userData);
    }
  );
  getByAdmin = catchAsync(
    async (req: Request, res: Response, next: NextFunction) => {
      const userData: LoginToken = req.body.user;
      await KTService.getByAdmin(req, res, userData);
    }
  );

  // Assign a KT Alert to a user
  assignTo = catchAsync(
    async (req: Request, res: Response, next: NextFunction) => {
      const { id } = req.params;
      const assignee = req.body.assigned_to;

      if (!assignee) {
        return res.status(400).json({
          status: "fail",
          message: "Assigned Id is required",
        });
      }

      await KTService.assignTo(id, assignee, res);
    }
  );

  // Acknowledge a KT Alert

  acknowledge = catchAsync(
    async (req: Request, res: Response, next: NextFunction) => {
      const { id } = req.params;
      await KTService.acknowledge(id, res);
    }
  );
}

export default new KTController();
