import { Router } from "express";
import ktController from "../controllers/kt.controller";
import jwtUtils from "../utils/jwtUtils";
import { allowedTo } from "../middlewares/allowedTo";
import { Roles } from "../utils/enum";
import catchAsync from "../utils/catchAsync";

export const KTRoute = Router();

// ✅ Apply authentication middleware (DO NOT wrap with catchAsync)
KTRoute.use(jwtUtils.jwtMiddleware); // ✅ no catchAsync here

// ✅ Routes
KTRoute.post("/", allowedTo(Roles.EMPLOYEE), ktController.create);
KTRoute.get("/", ktController.getAll);
KTRoute.patch("/:id/assign", allowedTo(Roles.MANAGER), ktController.assignTo);

// ✅ Role-based KT views
KTRoute.get(
  "/manager",
  allowedTo(Roles.MANAGER),
  ktController.getManagerAlerts
);
KTRoute.get(
  "/employee",
  allowedTo(Roles.EMPLOYEE),
  ktController.getEmployeeAlerts
);
KTRoute.get("/admin", allowedTo(Roles.ADMIN), ktController.getByAdmin);

KTRoute.patch(
  "/:id/acknowledge",
  allowedTo(Roles.EMPLOYEE),
  ktController.acknowledge
);
