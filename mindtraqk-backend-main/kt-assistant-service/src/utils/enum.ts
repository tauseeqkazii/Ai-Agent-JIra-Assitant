export enum KTPriority {
  Low = 'Low',
  Medium = 'Medium',
  High = 'High',
  Critical = 'Critical',
}

export enum KTStatus {
  Pending = 'Pending',
  InProgress = 'In Progress',
  Completed = 'Completed',
}

export enum Roles {
  SUPERADMIN = 'SUPERADMIN',
  EMPLOYEE = 'EMPLOYEE',
  MANAGER = 'MANAGER',
  ADMIN = 'ADMIN',
}

export enum AgentTaskState {
  AWAITING_UPDATE = 'awaiting_update',
  AWAITING_EDIT_DECISION = 'awaiting_edit_decision',
  AWAITING_EDIT_INPUT = 'awaiting_edit_input',
  AWAITING_CONFIRM = 'awaiting_confirm',
  COMPLETED = 'completed',
}
export enum Platforms {
  SLACK = 'slack',
  JIRA = 'jira',
  CLICKUP = 'clickup',
  ASANA = 'asana',
  GITHUB = 'github',
  MEET = 'meet',
  ZOOM = 'zoom',
  TEAMS = 'teams',
  MURALLYS = 'murallys',
}
