import { Request, Response, NextFunction } from 'express'
import { createMetricsClient } from '../utils/metrics'
import { Logger } from 'winston'
import { setupLogger } from '../utils/logger'

const metrics = createMetricsClient()
const logger: Logger = setupLogger()

export const aiMonitoringMiddleware = (
  req: Request,
  res: Response,
  next: NextFunction,
) => {
  const startTime = Date.now()

  res.on('finish', () => {
    const duration = Date.now() - startTime

    metrics.trackRequest({
      name: 'AI API Request',
      url: req.url,
      duration,
      resultCode: res.statusCode,
      success: res.statusCode < 400,
      properties: {
        userId: req.user?.id,
        endpoint: req.path,
        method: req.method,
      },
    })

    logger.info({
      message: 'AI API Request',
      url: req.url,
      duration,
      resultCode: res.statusCode,
      success: res.statusCode < 400,
      userId: req.user?.id,
      endpoint: req.path,
      method: req.method,
    })
  })

  next()
}
