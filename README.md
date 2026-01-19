# Flashduty Documentation

This repository contains the official documentation for [Flashduty](https://flashcat.cloud/), an incident management and on-call platform similar to PagerDuty. Built with [Mintlify](https://mintlify.com/).

## Documentation Structure

```
docs/
├── zh/                    # Chinese documentation
│   ├── home.mdx           # Homepage
│   ├── on-call/           # On-call product docs
│   ├── rum/               # RUM product docs
│   ├── monitors/          # Monitors product docs
│   ├── platform/          # Platform configuration
│   ├── openapi/           # API documentation
│   └── ...
├── en/                    # English documentation
│   └── (same structure as zh/)
├── logo/                  # Logo assets
└── docs.json              # Mintlify configuration
```

## Products

- **On-call**: Incident management, alert routing, escalation rules, and on-call scheduling
- **RUM**: Real User Monitoring for frontend performance and error tracking
- **Monitors**: Alert rules configuration for various data sources

## Development

### Prerequisites

Install the [Mintlify CLI](https://www.npmjs.com/package/mint):

```bash
npm i -g mint
```

### Local Preview

Run the following command at the root of this repository:

```bash
mint dev
```

View your local preview at `http://localhost:3000`.

### Check for Errors

```bash
mint broken-links
```

## Contributing

1. All documentation supports both Chinese (`zh/`) and English (`en/`) languages
2. Follow the existing file structure and naming conventions
3. Use Mintlify components for consistent styling
4. Test changes locally before submitting

## Resources

- [Flashduty Console](https://console.flashcat.cloud/)
- [Flashduty Website](https://flashcat.cloud/)
- [Mintlify Documentation](https://mintlify.com/docs)
