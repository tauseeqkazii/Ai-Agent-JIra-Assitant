// utils/redisClient.ts
import Redis from "ioredis";

const redis = new Redis({
  host: process.env.REDIS_HOST ||"127.0.0.1", // or your Redis host
  port: 6379,
  // password: "your_password", // if needed
});

export default redis;
