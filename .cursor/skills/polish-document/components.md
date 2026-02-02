# Mintlify Components Reference

Component selection guide and usage examples.

## Component Selection

| Scenario | Component | Description |
|----------|-----------|-------------|
| Step-by-step | `<Steps>` | Ordered instructions |
| Platform-specific | `<Tabs>` | macOS/Windows/Linux etc. |
| Multi-language code | `<CodeGroup>` | Same feature in different languages |
| Additional info | `<Accordion>` | Collapsible detailed content |
| Helpful notes | `<Note>` | Extra useful information |
| Best practices | `<Tip>` | Expert advice |
| Important warnings | `<Warning>` | Potential issues |
| Neutral info | `<Info>` | Background context |
| Success confirmation | `<Check>` | Completion status |
| Image display | `<Frame>` | Bordered image container |
| Link cards | `<Card>` / `<CardGroup>` | Related page navigation |

## Callout Components

### Note

```mdx
<Note>
Supplementary information that doesn't interrupt the main flow.
</Note>
```

### Tip

```mdx
<Tip>
Best practice recommendations to improve efficiency.
</Tip>
```

### Warning

```mdx
<Warning>
This operation is irreversible. Please proceed with caution.
</Warning>
```

### Info

```mdx
<Info>
Background information or neutral announcements.
</Info>
```

## Structure Components

### Steps

```mdx
<Steps>
<Step title="First step title">
  Detailed step description.
</Step>

<Step title="Second step title">
  Detailed step description.
  
  <Warning>
  Notes can be nested within steps.
  </Warning>
</Step>
</Steps>
```

### Tabs

Use Tabs for platform-specific content:

```mdx
<Tabs>
  <Tab title="macOS">
    Installation command for macOS (use bash code block)
  </Tab>
  <Tab title="Linux">
    Installation command for Linux (use bash code block)
  </Tab>
</Tabs>
```

Each Tab can contain code blocks with appropriate language identifiers.

### Accordion

```mdx
<AccordionGroup>
<Accordion title="FAQ 1">
  Answer content.
</Accordion>

<Accordion title="FAQ 2">
  Answer content.
</Accordion>
</AccordionGroup>
```

## Code Components

### Single Code Block

Use triple backticks with language and optional filename:

    ```python config.py
    API_KEY = os.environ.get('API_KEY')
    ```

### CodeGroup

Wrap multiple code blocks in CodeGroup for multi-language examples:

```mdx
<CodeGroup>
  (JavaScript code block with "Node.js" label)
  (Python code block with "Python" label)
</CodeGroup>
```

### Request/Response

Use RequestExample and ResponseExample for API documentation:

```mdx
<RequestExample>
  (cURL code block showing the request)
</RequestExample>

<ResponseExample>
  (JSON code block with status code, e.g., "200")
</ResponseExample>
```

## Media Components

### Frame

```mdx
<Frame>
<img src="/images/screenshot.png" alt="Feature screenshot description" />
</Frame>

<Frame caption="Image caption text">
<img src="/images/diagram.png" alt="Architecture diagram" />
</Frame>
```

### Video

```mdx
<video
  controls
  className="w-full aspect-video rounded-xl"
  src="https://example.com/video.mp4"
></video>
```

## Navigation Components

### Card

```mdx
<Card title="Quick Start" icon="rocket" href="/quickstart">
  Complete your first setup in 5 minutes.
</Card>
```

### CardGroup

```mdx
<CardGroup cols={2}>
<Card title="API Documentation" icon="code" href="/api">
  Complete API reference.
</Card>

<Card title="Integration Guide" icon="plug" href="/integrations">
  Third-party system integrations.
</Card>
</CardGroup>
```

## API Documentation

### ParamField

```mdx
<ParamField path="id" type="string" required>
  Unique resource identifier.
</ParamField>

<ParamField query="limit" type="integer" default="20">
  Result count limit, range 1-100.
</ParamField>
```

### ResponseField

```mdx
<ResponseField name="data" type="object">
  Response data object.
  
  <Expandable title="Properties">
    <ResponseField name="id" type="string">
      Resource ID.
    </ResponseField>
  </Expandable>
</ResponseField>
```
