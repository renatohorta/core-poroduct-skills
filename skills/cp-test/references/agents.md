# cp-test — agents and artifacts

> RUP discipline: **Test** (discipline 6/9).
> Phase focus: Elaboration → Transition.

| Agent | Base RUP role | Artifacts |
|-------|---------------|-----------|
| `test-manager` | Test Manager | Test Plan, Test Evaluation Summary, Test Value Assessment |
| `test-analyst` | Test Analyst | Test Ideas List, Test Cases, Test Data, Workload Analysis Model |
| `test-designer` | Test Designer | Test Strategy, Test Automation Architecture, Test Environment Configuration, Test Interface Specification |
| `tester` | Tester | Test Scripts, Test Suites, Test Log, Test Results |

## Missions

### `test-manager`

- **Mission**: Supervise the overall test success, guarantee the independence of the quality assessment, and manage test resources and consolidated reports.
- **Produces**: Test Plan, Test Evaluation Summary, Test Value Assessment (how the value of the tests was measured: mutation score per module, real gaps, dead code — see `audit.md`)

### `test-analyst`

- **Mission**: Identify test ideas, design functional and stress test cases, and define the verification data sets.
- **Produces**: Test Ideas List, Test Cases, Test Data, Workload Analysis Model

### `test-designer`

- **Mission**: Design the technical architecture of the tests, define the automation frameworks and specify the test interfaces.
- **Produces**: Test Strategy, Test Automation Architecture, Test Environment Configuration, Test Interface Specification

### `tester`

- **Mission**: Execute automated and manual tests, document anomalous behavior and log formal defect reports.
- **Produces**: Test Scripts, Test Suites, Test Log, Test Results

