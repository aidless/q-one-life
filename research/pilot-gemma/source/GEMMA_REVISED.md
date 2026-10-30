# Your Tool-Selection Benchmark May Be Scoring Wrong Calls as Correct

## Abstract

Substring matching can credit the name of one tool when an output contains only a longer identifier, such as `get_stock_v1` instead of `get_stock`. We audit a published archive of 450 tool-selection records and distinguish this string-scoring defect from semantic correctness of an executed call. Twelve recorded positives contain only a longer identifier while the complete recorded output lacks the gold identifier. Twelve further positives cannot be resolved from the truncated record. These counts support a discrepancy between substring and whole-identifier scoring; they do not establish execution accuracy. The archive also contains only 75 distinct record signatures when grouped by registry size, each repeated six times. Because prompts and row-level registries are absent, independence of the underlying trials cannot be established. We therefore withdraw independent-trial significance claims and release a reproducible audit, negative controls, and a record format for stronger future evaluation.

## 1. Question and scope

Tool registries can contain nested names: `get_weather` and `get_weather_v1` are different identifiers. The audited rule marks an output positive whenever the gold name occurs anywhere in its text. This credits a shorter name inside a longer one.

A whole-identifier rule removes that particular collision. It still does not determine which tool was invoked. For example, “get_weather exists, but I will use calculate” mentions the gold identifier without choosing it. Correct arguments, execution, and successful task completion require additional evidence. Our original wording sometimes treated identifier presence as proof of a genuine call; that interpretation was too strong.

## 2. Evidence and reproducible procedure

The [published evidence kit](https://www.kaggle.com/datasets/liuzewen123/toolselect-audit), licensed Apache-2.0, contains three JSONL files, a scorer, a replay script, and tests. The [companion notebook](https://www.kaggle.com/code/liuzewen123/toolselect-audit-recompute) runs on CPU. The archive describes its upstream model as a Qwen2.5-1.5B base with an adapter. This audit replays the preserved records; it does not reproduce or independently authenticate upstream model inference.

Each record preserves `gold_tool`, `verdict`, `output`, and `called`. It omits the original request, full per-row registry, and unique trial identifier. Output is capped at 200 characters. These omissions limit what can be reconstructed.

We first run the scorer's fixtures and then inject a broken implementation that substitutes substring matching for strict matching. The normal fixtures pass; the injected defect triggers five of eighteen assertions. A separate negative control reverses the truncation-adjudication order and is detected by its fixtures. These controls demonstrate that the tests can reject the specified defects.

We then recompute all record counts, hash the input files, inspect truncation, and count duplicate record signatures. A signature includes registry size and the complete preserved JSON record. It is a diagnostic of the archive, not proof that two original requests were identical.

## 3. Results that the record supports

For positives recorded by the substring rule, we distinguish three cases: the gold identifier is visibly present as a whole token; it is absent from a fully preserved output that contains only a longer name; or its presence in a lost tail remains unresolved.

| Registry size | Records | Recorded substring positives | Whole gold identifier observed | Longer-name discrepancy | Unresolved |
|---:|---:|---:|---:|---:|---:|
| 5 | 30 | 24 | 18 | 0 | 6 |
| 20 | 120 | 60 | 48 | 12 | 0 |
| 50 | 300 | 36 | 30 | 0 | 6 |
| Total | 450 | 120 | 96 | 12 | 12 |

The twelve discrepancies are six repeated records involving `get_stock_v1` and six involving `get_news_v1`. They represent two distinct preserved signatures, not twelve distinct observed failure mechanisms. Across all records, the visible whole-identifier hit fractions are 60%, 40%, and 10%. Those are text-measurement results, not semantic tool-call accuracies.

Conditional on the archived verdict field having been computed from the full generation as documented upstream, the positive records permit between twelve and twenty-four substring-versus-identifier discrepancies. The archive cannot verify that upstream computation from the missing full outputs. We therefore report the condition explicitly rather than presenting this interval as a bound on true execution accuracy.

## 4. Duplication and independence

Within registry sizes 5, 20, and 50, the preserved records have five, twenty, and fifty distinct signatures, respectively. Every signature occurs six times. There are consequently seventy-five distinct registry-size/record pairs among the 450 rows.

This does not prove that the upstream generator copied data: distinct prompts could produce the same preserved output. It does mean that the package lacks the inputs needed to establish independent observations. Earlier trend-test p-values treated the rows as independent trials. We withdraw those inferential claims. Descriptive counts remain reproducible, but they cannot support an architecture comparison, a general model-capability claim, or a population error rate.

The archive's recorded omission and hallucination buckets are also heuristic text classifications. In particular, truncated text and missing registries prevent a complete semantic reconstruction. Their counts should be described as properties of this record and scorer, rather than confirmed task-failure categories.

## 5. Cross-model and cross-registry diagnostic

We additionally collected 48 fresh local outputs from two installed quantized models, `qwen2.5:1.5b-instruct-q4_K_M` and `llama3.2:1b`. Six synthetic requests cover weather operations and repository operations. Each request is paired across flat versus nested tool names and registry sizes five versus twenty. Temperature is zero, the seed is fixed, and one response is generated per condition. Full requests, ordered registries, responses, model digests, decoding settings, and parsed outputs are retained.

The requested response contract is one JSON object containing `tool` and `arguments`. Qwen satisfies the specified tool field with the expected name on 22/24 conditions, with matching arguments on 21/24. Llama does so on 10/24 and 7/24, respectively. Six Llama outputs use an alternate JSON shape; these are reported as contract-format discrepancies, not automatically as semantic mis-selections. These tiny paired diagnostics do not establish a model ranking.

Among responses containing a valid string in the required `tool` field but selecting the wrong tool, substring matching produces one false positive for Qwen and three for Llama. They include both weather and repository registries: the model selects a suffixed identifier while the gold identifier is its shorter prefix. Whole-identifier matching avoids these four suffix collisions. It still does not demonstrate tool execution or task success.

This diagnostic extends the collision check to another model family and another registry. It is not a replication of the archived adapter experiment. Only six requests were used, and registry conditions are paired on those same requests, so we report descriptive counts without independent-trial significance tests.

## 6. A stronger evaluation record

A future cross-model and cross-registry evaluation should save the full request, ordered tool schemas, gold action with arguments, raw generation, parsed invocation, execution trace, task outcome, model and adapter versions, decoding settings, and a unique trial identifier. Text matching and execution-based correctness should be reported separately.

Larger request sets, additional models, and execution-based tests remain future work. Registry families should include names without collisions as a control, names with version suffixes, and structured names whose punctuation matters. Repeated decoding should be distinguished from distinct requests. All grouping and uncertainty calculations must use the actual independent experimental unit.

## 7. Related evaluation work

The [Berkeley Function Calling Leaderboard](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard) evaluates function calling using structured and executable evaluation. [SWE-bench](https://github.com/SWE-bench/SWE-bench) evaluates real repository issues using a reproducible testing environment. Our audit addresses an earlier layer: what a preserved text record can support about identifier selection. Neither identifier presence nor compliance with a small JSON contract substitutes for those execution-based outcomes.

## 8. Conclusion

The demonstrated result is a reproducible string-scoring defect: substring containment can credit a shorter tool identifier found only inside a longer one. Tokenization repairs that collision, but it does not establish correct tool invocation. Truncation, missing inputs, and repeated preserved records restrict stronger claims. Publishing those restrictions alongside the replay is more useful than reporting an accuracy that the evidence cannot justify.
