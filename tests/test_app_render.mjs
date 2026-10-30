import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = fs.readFileSync("src/qone_life/static/app.js", "utf8");
const renderFunctions = source.split("document.addEventListener('click'")[0];
const consumerSource = fs.readFileSync(
  "src/qone_life/static/consumer.js",
  "utf8",
);

test("training evidence summary exposes denominators and exclusion reasons", () => {
  const probe = `
const forecast={
  training_n:39,
  portfolio_support:9,
  predictions:{practice:{lower:5.6,upper:15.8,unit:"条"}},
  training_evidence:{
    summary:{available_n:40,trainable_n:39,excluded_n:1},
    excluded_episodes:[{episode_id:"e25",issues:[
      {code:"observation_conflict"},
      {code:"before_reference_not_current"}
    ]}]
  }
};
const evidenceHTML=trainingEvidence(forecast);
S={planner:{system:{goal_order:[],goals:[],state:{resources:{},measures:{}}}}};
const systemHTML=systemEvidence({system_costs:{},system_forecast:forecast});
({evidenceHTML,systemHTML});
`;
  const {evidenceHTML, systemHTML} = vm.runInNewContext(renderFunctions + probe);

  assert.match(evidenceHTML, /可训练 39 条 \/ 可用 40 条；排除 1 条。/);
  assert.match(
    evidenceHTML,
    /e25：同一测量同一时点存在未解决冲突；事前引用不是行动开始时的当前观察/,
  );
  assert.match(systemHTML, /学习证据资格/);
});

test("consumer locale dictionaries keep the same keys", () => {
  const zh = JSON.parse(
    fs.readFileSync("src/qone_life/static/zh-CN.json", "utf8"),
  );
  const en = JSON.parse(
    fs.readFileSync("src/qone_life/static/en-US.json", "utf8"),
  );
  assert.deepEqual(Object.keys(zh).sort(), Object.keys(en).sort());
  for (const key of Object.keys(zh)) {
    assert.ok(zh[key].trim(), `missing zh-CN copy for ${key}`);
    assert.ok(en[key].trim(), `missing en-US copy for ${key}`);
  }
});

test("onboarding keeps the goal action default and skip copy explicit", async () => {
  const onboardingStart = consumerSource.indexOf("function onboardingGoal()");
  const onboardingEnd = consumerSource.indexOf("function renderToday()");
  assert.ok(onboardingStart >= 0 && onboardingEnd > onboardingStart);
  const onboarding = consumerSource.slice(onboardingStart, onboardingEnd);
  assert.doesNotMatch(onboarding, /t\(['"]common\.skip['"]\)/);
  assert.ok(onboarding.includes("common.skipAction"));

  const submitStart = consumerSource.indexOf("async function submitGoal(form)");
  const submitEnd = consumerSource.indexOf("async function handleSubmit(event)");
  assert.ok(submitStart >= 0 && submitEnd > submitStart);
  const submitSource = consumerSource.slice(submitStart, submitEnd);
  let captured;
  const context = {
    FormData: class {
      constructor(form) {
        this.form = form;
      }

      *[Symbol.iterator]() {
        yield* Object.entries(this.form.values);
      }
    },
    api: async (path, options) => {
      captured = { path, options };
    },
  };
  vm.runInNewContext(`${submitSource}\n({submitGoal});`, context);
  await context.submitGoal({
    dataset: {},
    values: {
      title: "First goal",
      success_criterion: "A checked result",
      domain: "learning",
    },
  });
  assert.equal(captured.path, "goals");
  assert.equal(captured.options.method, "POST");
  assert.equal(JSON.parse(captured.options.body).priority, 3);
});
