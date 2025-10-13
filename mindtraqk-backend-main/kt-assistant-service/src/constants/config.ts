const corsOptions = {
  origin: [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:3001",
    "https://accounts.google.com",
    "https://app.mindtraqk.com",
    process.env.FRONTEND_URL,
  ],
  methods: ["GET", "POST", "PUT", "DELETE", "PATCH"],
  credentials: true,
  allowedHeaders: ["Content-Type", "Authorization"],
};

export { corsOptions };
