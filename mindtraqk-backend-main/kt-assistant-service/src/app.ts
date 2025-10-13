import express, { Request, Response, NextFunction } from 'express'
import { connection } from './utils/database'
import dotenv from 'dotenv'
import morgan from 'morgan'
import cookieParser from 'cookie-parser'
import { rootRoute } from './routes/Root.routes'
import { corsOptions } from './constants/config'
import cors from 'cors'
import aiRoutes from './routes/ai.routes'
import { aiMonitoringMiddleware } from './middleware/ai-monitoring'
import helmet from 'helmet'
import compression from 'compression'

dotenv.config()

const app = express()

// Middleware to parse JSON
app.use(express.json())
app.use(cookieParser())
app.use(cors(corsOptions))
app.use(helmet())
app.use(compression())

// Connect to the database
connection()

// Log all API requests
if (process.env.NODE_ENV === 'development') {
  app.use(morgan('dev')) // short, colored logs
} else {
  // For production or log files, use 'combined'
  app.use(morgan('combined'))
}

// Basic test route
app.get('/', (req: Request, res: Response) => {
  res.send('✅ KT Assistant Service is up and running!')
})

app.use('/api/v1', rootRoute)

// Add monitoring middleware
app.use('/api/v1/ai', aiMonitoringMiddleware)

// Add AI routes
app.use('/api/v1', aiRoutes)

// Global error handler (optional)
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  console.error(err.stack)
  res.status(500).json({ error: 'Something went wrong!' })
})

// Start server
const PORT = process.env.PORT || 8181
app.listen(PORT, () => {
  console.log(`🚀 KT Assistant Service listening on port the  ${PORT}`)
})
