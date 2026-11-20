import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
const workflow = JSON.parse(
  readFileSync(
    new URL(
      "../../files/integrations/n8n/flashduty-error-workflow.json",
      import.meta.url,
    ),
  ),
);
const node = (name) => workflow.nodes.find((n) => n.name === name);
const prepare = new Function(
  "$json",
  "$execution",
  node("Prepare alert").parameters.jsCode,
);
const check = new Function("$json", node("Check response").parameters.jsCode);
const payload = (id = "231") => ({
  workflow: { id: "wf-1", name: "Order sync" },
  execution: {
    id,
    url: "https://n8n.example.com/execution/231",
    error: { message: "Request failed" },
    lastNodeExecuted: "HTTP Request",
  },
  instance_id: "production",
  severity: "Warning",
});
const convert = (data = payload(), id = "handler-1") =>
  prepare(data, { id }).json;
test("distinct_delivery_identity", () => {
  assert.notEqual(
    convert(payload("231")).alert_key,
    convert(payload("232")).alert_key,
  );
  const a = payload();
  a.instance_id = "staging";
  assert.notEqual(convert(a).alert_key, convert().alert_key);
  const b = payload();
  b.workflow.id = "wf-2";
  assert.notEqual(convert(b).alert_key, convert().alert_key);
  assert.equal(
    convert(payload(), "handler-1").alert_key,
    convert(payload(), "handler-2").alert_key,
  );
});
test("mutable_field_invariance", () => {
  const a = payload();
  a.workflow.name = "Renamed";
  a.execution.error.message = "Different";
  a.execution.lastNodeExecuted = "Other";
  a.severity = "Critical";
  assert.equal(convert(a).alert_key, convert().alert_key);
});
test("trigger_failure_without_execution_identity", () => {
  const a = {
    workflow: { id: "wf-1", name: "Order sync" },
    trigger: { error: { message: "Activation failed" } },
    instance_id: "production",
    severity: "Warning",
  };
  assert.match(convert(a).description, /Activation failed/);
  assert.notEqual(
    convert(a, "handler-1").alert_key,
    convert(a, "handler-2").alert_key,
  );
  assert.equal(convert(a).labels.failure_type, "trigger");
  assert.throws(() => convert(a, ""), /identity/i);
});
test("missing_identity", () => {
  for (const edit of [
    (p) => delete p.workflow.id,
    (p) => delete p.execution.id,
    (p) => (p.instance_id = ""),
    (p) => (p.instance_id = "YOUR_INSTANCE_ID"),
  ]) {
    const p = payload();
    edit(p);
    assert.throws(() => convert(p), /identity|instance/i);
  }
  const p = payload();
  p.execution.id = 123;
  assert.equal(convert(p).labels.execution_id, "123");
  const p2 = payload();
  p2.instance_id = "x".repeat(256);
  assert.throws(() => convert(p2), /length|long/i);
});
test("severity_mapping", () => {
  for (const value of ["Critical", "Warning", "Info"]) {
    const p = payload();
    p.severity = value;
    assert.equal(convert(p).event_status, value);
  }
  for (const value of ["Ok", "warning", "", null, "unknown"]) {
    const p = payload();
    p.severity = value;
    assert.throws(() => convert(p), /severity/i);
  }
});
test("labels_mapping_and_sensitive_fields", () => {
  const p = payload();
  p.execution.error.stack = "secret-stack";
  p.execution.error.context = { secret: "private" };
  const a = convert(p);
  assert.equal(a.labels.integration, "n8n");
  assert.equal(a.labels.workflow_id, "wf-1");
  assert.equal(a.labels.instance_id, "production");
  assert.equal(a.labels.execution_id, "231");
  assert.doesNotMatch(JSON.stringify(a), /secret-stack|private/);
  assert.match(a.description, /https:\/\/n8n.example.com\/execution\/231/);
  p.execution.url =
    "https://n8n.example.com/execution/231?token=secret#fragment";
  assert.doesNotMatch(convert(p).description, /token=|secret|fragment/);
  p.execution.error.message = "x".repeat(5000);
  assert.ok(convert(p).description.length <= 2048);
});
test("response_body_errors_are_visible", () => {
  assert.throws(
    () => check({ error: { code: 1, message: "Invalid integration key" } }),
    /Flashduty rejected/,
  );
  assert.throws(() => check({}), /confirmation/i);
  assert.throws(
    () => check({ data: { alert_key: "different" } }),
    /confirmation/i,
  );
  assert.equal(
    check({ request_id: "request-1", data: { alert_key: "key" } }).json
      .request_id,
    "request-1",
  );
});
test("template_transport_contract", () => {
  const send = node("Send to Flashduty");
  assert.equal(send.retryOnFail, true);
  assert.equal(send.maxTries, 3);
  assert.equal(send.parameters.authentication, "genericCredentialType");
  assert.equal(send.parameters.genericAuthType, "httpQueryAuth");
  assert.equal(send.parameters.method, "POST");
  assert.equal(send.parameters.options.timeout, 10000);
  assert.equal(send.continueOnFail, undefined);
  assert.equal(workflow.active, false);
  assert.doesNotMatch(JSON.stringify(workflow), /integration_key=[^&"{} ]{8,}/);
  assert.equal(
    workflow.nodes.filter((n) => n.type === "n8n-nodes-base.errorTrigger")
      .length,
    1,
  );
  assert.equal(
    workflow.connections["Prepare alert"].main[0][0].node,
    "Send to Flashduty",
  );
});

test("workflow_names_are_literal_titles", () => {
  for (const name of [
    "prod::orders",
    "sync [TPL]{{bad}}",
    "$service",
    "订单同步",
  ]) {
    const p = payload();
    p.workflow.name = name;
    const event = convert(p);
    assert.equal(event.title, `n8n workflow failed: ${name}`);
    assert.equal(event.title_rule, undefined);
  }
});

test("distinct_rule_resource", () => {
  const changedWorkflow = payload();
  changedWorkflow.workflow.id = "different-workflow";
  const changedInstance = payload();
  changedInstance.instance_id = "different-instance";
  assert.notEqual(convert(changedWorkflow).alert_key, convert().alert_key);
  assert.notEqual(convert(changedInstance).alert_key, convert().alert_key);
});
test("map_order_invariance", () => {
  const original = payload();
  const reordered = Object.fromEntries(Object.entries(original).reverse());
  reordered.workflow = Object.fromEntries(
    Object.entries(original.workflow).reverse(),
  );
  reordered.execution = Object.fromEntries(
    Object.entries(original.execution).reverse(),
  );
  assert.equal(convert(reordered).alert_key, convert(original).alert_key);
});
