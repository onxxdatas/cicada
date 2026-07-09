---
name: Performance Issue
about: Report performance problems while running load tests.Describe this issue template's
  purpose here.
title: ''
labels: enhancement
assignees: ''

---

````md
---
name: Performance Issue
about: Report performance, scalability, or load testing issues in Cicada.
title: "[Performance] "
labels: performance
assignees: ""

---

## Describe the performance issue

Provide a clear and concise description of the performance problem.

## To Reproduce

Steps to reproduce the issue:

1. Configure a load test with '...'
2. Set virtual users to '...'
3. Start the test
4. Observe the performance issue

## Expected performance

Describe what performance you expected (e.g. expected RPS, latency, resource usage).

## Actual performance

Describe what actually happened (e.g. low throughput, high latency, errors, UI freezing).

## Test Configuration

- Target URL:
- HTTP Method:
- Virtual Users (VUs):
- Test Duration:
- Load Stages:
- Request Body (if applicable):

## Environment

- Cicada Version:
- Docker Version:
- Operating System:
- Browser:

## Resource Usage (if known)

- CPU Usage:
- Memory Usage:
- Disk Usage:
- Network Usage:

## Logs

If applicable, include relevant backend logs, Docker logs, or k6 output.

```text
Paste logs here
````

## Screenshots

If applicable, add screenshots, graphs, or recordings that help explain the issue.

## Additional Context

Add any other context about the performance issue here.

```
```
