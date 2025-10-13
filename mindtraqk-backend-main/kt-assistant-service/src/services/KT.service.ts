import { Response } from "express";
import { z } from "zod";
import ResponseHandler from "../utils/apiResponse";
import { KTModel } from "../models/kt.models";
import { ktAlertValidation } from "../utils/validation";
import APIfeatures from "../utils/apiFeatures";
import { KTStatus } from "../utils/enum";
import { LoginToken } from "../types/types";
import { UserModel } from "../models/User.model";

class KTService {
  async create(
    ktData: z.infer<typeof ktAlertValidation>,
    res: Response,
    userData: LoginToken
  ) {
    try {
      const newAlert = await KTModel.create({
        ...ktData,
        user: userData.id,
        reporting_manager: userData.reportingTo,
      });

      return ResponseHandler.success(
        res,
        "KT Alert created successfully",
        newAlert,
        201
      );
    } catch (error: any) {
      return ResponseHandler.internalError(
        res,
        "Failed to create KT Alert",
        error
      );
    }
  }

  async getAll(req: any, res: Response) {
    try {
      const userData: LoginToken = req.body.user;

      // 1️⃣ find all user IDs in this tenant
      const tenantUserIds = await UserModel.find({
        Tenant: userData.Tenant,
      }).distinct("_id");

      // 2️⃣ base query restricted to those IDs
      const baseQuery = KTModel.find({
        user: { $in: tenantUserIds },
      })
        .populate("user")
        .populate("assigned_to")
        .populate("reporting_manager");

      // 3️⃣ apply filtering/search/sort/fields/pagination
      const features = new APIfeatures(baseQuery, req.query)
        .filter()
        .search()
        .sort()
        .limitFields()
        .pagination();

      // 4️⃣ execute paginated query
      const alerts = await features.query;

      // 5️⃣ count total matching before pagination
      const countFeatures = new APIfeatures(
        KTModel.find({ user: { $in: tenantUserIds } }),
        req.query,
        true // forCount = true → uses countDocuments under the hood
      )
        .filter()
        .search();
      const totalCount = await countFeatures.query.countDocuments();

      // 6️⃣ return both results and total count
      return ResponseHandler.success(res, "Fetched KT Alerts", {
        results: alerts.length,
        total: totalCount,
        alerts,
      });
    } catch (error: any) {
      console.error("KTService.getAll error:", error);
      return ResponseHandler.internalError(
        res,
        "Failed to fetch KT Alerts",
        error
      );
    }
  }

  async assignTo(alertId: string, assignee: string, res: Response) {
    try {
      const updated = await KTModel.findByIdAndUpdate(
        alertId,
        {
          assigned_to: assignee,
          status: KTStatus.InProgress,
        },
        { new: true }
      );

      if (!updated) {
        return ResponseHandler.notFound(res, "KT Alert not found");
      }

      return ResponseHandler.success(
        res,
        "KT Alert assigned successfully",
        updated
      );
    } catch (error: any) {
      return ResponseHandler.internalError(
        res,
        "Failed to assign KT Alert",
        error
      );
    }
  }
  async getByManager(req: any, res: Response, userData: LoginToken) {
    try {
      const query = KTModel.find({
        reporting_manager: userData.id,
      })
        .populate("user")
        .populate("assigned_to")
        .populate("reporting_manager");

      const features = new APIfeatures(query, req.query)
        .filter()
        .search()
        .sort()
        .limitFields()
        .pagination();

      const alerts = await features.query;

      return ResponseHandler.success(
        res,
        "Fetched KT Alerts for manager",
        alerts
      );
    } catch (error: any) {
      return ResponseHandler.internalError(
        res,
        "Failed to fetch manager KT Alerts",
        error
      );
    }
  }

  async getByEmployee(req: any, res: Response, userData: LoginToken) {
    try {
      const query = KTModel.find({
        user: userData.id,
      })
        .populate("user")
        .populate("assigned_to")
        .populate("reporting_manager");

      const features = new APIfeatures(query, req.query)
        .filter()
        .search()
        .sort()
        .limitFields()
        .pagination();

      const alerts = await features.query;

      return ResponseHandler.success(
        res,
        "Fetched KT Alerts for employee",
        alerts
      );
    } catch (error: any) {
      return ResponseHandler.internalError(
        res,
        "Failed to fetch employee KT Alerts",
        error
      );
    }
  }

  async getByAdmin(req: any, res: Response, userData: LoginToken) {
    try {
      const tenantUserIds = await UserModel.find({
        Tenant: userData.Tenant,
      }).distinct("_id");

      // 3️⃣ build base query restricted to tenant users
      const baseQuery = KTModel.find({
        user: { $in: tenantUserIds },
      })
        .populate("user")
        .populate("assigned_to")
        .populate("reporting_manager");

      // 4️⃣ apply filtering / search / sort / fields / pagination
      const features = new APIfeatures(baseQuery, req.query)
        .filter()
        .search()
        .sort()
        .limitFields()
        .pagination();

      const alerts = await features.query;

      // 5️⃣ total count before pagination
      const countFeatures = new APIfeatures(
        KTModel.find({ user: { $in: tenantUserIds } }),
        req.query,
        true // forCount → uses countDocuments()
      )
        .filter()
        .search();
      const totalCount = await countFeatures.query.countDocuments();

      // 6️⃣ send response
      return ResponseHandler.success(res, "Fetched all KT Alerts", {
        results: alerts.length,
        total: totalCount,
        alerts,
      });
    } catch (error: any) {
      console.error("KTService.getByAdmin error:", error);
      return ResponseHandler.internalError(
        res,
        "Failed to fetch KT Alerts for admin",
        error
      );
    }
  }

  async acknowledge(alertId: string, res: Response) {
    try {
      const alert = await KTModel.findById(alertId);

      if (!alert) {
        return ResponseHandler.notFound(res, "KT Alert not found");
      }

      const updated = await KTModel.findByIdAndUpdate(
        alertId,
        {
          is_acknowledged: true,
          status: KTStatus.Completed,
        },
        { new: true }
      )
        .populate("user")
        .populate("assigned_to")
        .populate("reporting_manager");

      if (!updated) {
        return ResponseHandler.notFound(res, "KT Alert not found");
      }

      return ResponseHandler.success(
        res,
        "KT Alert acknowledged and marked as completed",
        updated
      );
    } catch (error: any) {
      return ResponseHandler.internalError(
        res,
        "Failed to acknowledge KT Alert",
        error
      );
    }
  }
}

export default new KTService();
