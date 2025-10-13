import axios from "axios";
import dotenv from "dotenv";
dotenv.config();

const CLIENT_ID = process.env.JIRA_CLIENT_ID as string;
const CLIENT_SECRET = process.env.JIRA_CLIENT_SECRET as string;

export async function ensureValidJiraAccessToken(
  tokenDoc: any
): Promise<string> {
  const expiresAt = new Date(tokenDoc.expiresAt).getTime();
  const now = Date.now();

  if (!tokenDoc.refreshToken) {
    throw new Error("Missing refresh token for Jira integration.");
  }

  if (!tokenDoc.accessToken || now > expiresAt - 60_000) {
    console.log("🔄 Refreshing Jira access token…");
    const refreshRes = await axios.post(
      "https://auth.atlassian.com/oauth/token",
      {
        grant_type: "refresh_token",
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
        refresh_token: tokenDoc.refreshToken,
      }
    );

    tokenDoc.accessToken = refreshRes.data.access_token;
    tokenDoc.refreshToken = refreshRes.data.refresh_token;
    tokenDoc.expiresAt = new Date(now + refreshRes.data.expires_in * 1000);
    await tokenDoc.save();

    console.log("✅ Jira access token refreshed");
  }

  return tokenDoc.accessToken;
}
