import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = fs.readFileSync("src/qone_life/static/app.js", "utf8");
const renderFunctions = source.split("document.addEventListener('click'")[0];

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
