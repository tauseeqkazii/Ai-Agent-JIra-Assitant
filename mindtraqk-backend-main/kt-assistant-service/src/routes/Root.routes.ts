import { Router } from "express";
import { assistantRoute } from "./Assistant.route";
import { KTRoute } from "./Kt.routes";
import { AgentRoute } from "./Agent.route";

const rootRoute = Router();

rootRoute.use("/assistant", assistantRoute);
rootRoute.use("/kt-alerts", KTRoute);
rootRoute.use("/agent", AgentRoute);

export { rootRoute };
