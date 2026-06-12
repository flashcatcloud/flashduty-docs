---
title: "Jira Issue Events"
description: "Sync Jira Issue events to Flashduty via webhooks to collect change events."
date: "2025-05-19T10:00:00+08:00"
url: "https://docs.flashcat.cloud/en/flashduty/jira-integration-guide"
---

Synchronize Jira Issue events to Flashduty via webhooks to collect change events.

## Limitations

### In Jira

- You must have permission to modify **Settings=>System=>Webhooks**.
- For self-hosted deployments, your Jira server must be able to access the domain api.flashcat.cloud.

## Supported versions

This guide is compatible with both **Jira Cloud and self-hosted** versions.

## Setup steps

### In Flashduty

1. Go to the Flashduty console, select **Integration Center=>Change Events** to enter the integration selection page.
2. Select **Jira** integration:
   - **Integration name**: Define a name for this integration.
3. Click **Save** and copy the newly generated **push URL** for later use.
4. Done.

### In Jira

1. Log in to your Jira.
2. Go to **Settings=>System=>Webhooks** page, and click the Create button.
3. Enter the callback URL as the push URL from your integration, and check Issue Created/Updated/Deleted event types.
4. Optionally, enter JQL to further narrow down the scope of events to sync, such as specific projects.
5. Click the Save button to submit the configuration.

![Jira webhook](http://download.flashcat.cloud/jira-webhook.png)

## Status mapping

Flashduty extracts the status.name information from the webhook payload by default and converts the status according to the following mapping:

| Jira        | Flashduty   | Status               |
| ----------- | ----------- | -------------------- |
| planned     | planned     | Created              |
| to do       | planned     | Created              |
| ready       | ready       | About to start       |
| processing  | processing  | In progress          |
| open        | processing  | In progress          |
| reopen      | processing  | In progress          |
| in progress | processing  | In progress          |
| canceled    | canceled    | Canceled/rolled back |
| aborted     | canceled    | Canceled/rolled back |
| done        | done        | Completed            |
| resolved    | done        | Completed            |
| closed      | done        | Completed            |

Please contact Flashduty if you want to modify this mapping.
