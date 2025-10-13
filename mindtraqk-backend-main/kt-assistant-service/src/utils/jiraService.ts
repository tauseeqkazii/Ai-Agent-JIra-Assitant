import axios from "axios";
import IntegrationToken from "../models/Integration.model";
import { ensureValidJiraAccessToken } from "./jirautils";
import { Platforms } from "./enum";
import { LoginToken } from "../types/types";

class JiraService {
  // ---------- Helper to get cloudId and authHeader ----------
  private async getCloudResource(tokenDoc: any) {
    const validAccessToken = await ensureValidJiraAccessToken(tokenDoc);
    const authHeader = { Authorization: `Bearer ${validAccessToken}` };

    const resourcesResp = await axios.get(
      "https://api.atlassian.com/oauth/token/accessible-resources",
      { headers: authHeader }
    );
    const resource = resourcesResp.data.find((r: any) => r.id && r.url);
    if (!resource) throw new Error("No accessible Jira resource found");

    return { cloudId: resource.id, jiraBase: resource.url, authHeader };
  }

  // ---------- Get pending tasks for a user ----------
  async getPendingTasks(userId: string) {
    const tokenDoc = await IntegrationToken.findOne({
      user: userId,
      platform: Platforms.JIRA,
    });
    if (!tokenDoc) throw new Error("Jira integration not found");

    const { cloudId, authHeader } = await this.getCloudResource(tokenDoc);
    const accountId = tokenDoc.profileData.accountId;

    const jql = `assignee = ${accountId} AND status = "In Progress" AND created >= -7d`;

    const { data } = await axios.post(
      `https://api.atlassian.com/ex/jira/${cloudId}/rest/api/3/search/jql`,
      {
        jql,
        maxResults: 50,
        fields: ["summary", "status", "created", "updated"],
      },
      { headers: authHeader }
    );

    return data.issues.map((issue: any) => ({
      taskId: issue.key,
      title: issue.fields.summary,
      status: issue.fields.status?.name || "",
      createdAt: issue.fields.created,
      updatedAt: issue.fields.updated,
    }));
  }

  // ---------- Update task summary in Jira ----------
  async updateTask(
    taskId: string,
    action: { type: "comment" | "status" | "fields"; value: any },
    userData: LoginToken
  ) {
    const tokenDoc = await IntegrationToken.findOne({
      user: userData.id,
      platform: Platforms.JIRA,
    });
    if (!tokenDoc) throw new Error("Jira integration not found");

    const { cloudId, authHeader } = await this.getCloudResource(tokenDoc);

    switch (action.type) {
      case "comment":
        await axios.post(
          `https://api.atlassian.com/ex/jira/${cloudId}/rest/api/3/issue/${taskId}/comment`,
          {
            body: {
              type: "doc",
              version: 1,
              content: [
                {
                  type: "paragraph",
                  content: [
                    {
                      type: "text",
                      text: action.value,
                    },
                  ],
                },
              ],
            },
          },
          { headers: authHeader }
        );
        break;

      case "status":
        await axios.post(
          `https://api.atlassian.com/ex/jira/${cloudId}/rest/api/3/issue/${taskId}/transitions`,
          { transition: { id: action.value } },
          { headers: authHeader }
        );
        break;

      case "fields":
        if (action.value.summary) delete action.value.summary;
        await axios.put(
          `https://api.atlassian.com/ex/jira/${cloudId}/rest/api/3/issue/${taskId}`,
          { fields: action.value },
          { headers: authHeader }
        );
        break;

      default:
        throw new Error("Unsupported update type");
    }
  }

  // ---------- Add a comment helper ----------
  async addComment(taskId: string, comment: string, userData: LoginToken) {
    return this.updateTask(
      taskId,
      { type: "comment", value: comment },
      userData
    );
  }

  // ---------- Get transition ID for a given status ----------
  async getTransitionId(
    taskId: string,
    statusName: string,
    userData: LoginToken
  ) {
    const tokenDoc = await IntegrationToken.findOne({
      user: userData.id,
      platform: Platforms.JIRA,
    });
    if (!tokenDoc) throw new Error("Jira integration not found");

    const { cloudId, authHeader } = await this.getCloudResource(tokenDoc);

    const { data } = await axios.get(
      `https://api.atlassian.com/ex/jira/${cloudId}/rest/api/3/issue/${taskId}/transitions`,
      { headers: authHeader }
    );

    const transition = data.transitions.find(
      (t: any) => t.to.name === statusName
    );
    if (!transition)
      throw new Error(`Transition to status "${statusName}" not found`);
    return transition.id;
  }
}

export default new JiraService();
