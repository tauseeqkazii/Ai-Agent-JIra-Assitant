import Redis from 'ioredis'
import dotenv from 'dotenv'

dotenv.config()

export const setupRedis = () => {
  const redis = new Redis(process.env.REDIS_URL!, {
    password: process.env.REDIS_PASSWORD,
    retryStrategy: (times) => Math.min(times * 50, 2000),
  })

  redis.on('error', (err) => console.error('Redis Client Error:', err))
  return redis
}
