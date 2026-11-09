# Failure modes

These are current behaviors of this tree. They are limits, not a claim that the interface prevents them.

## Model text can be shown as a recommendation

Automatic planning asks a local model for 1–3 actions, then `validate_plan` checks shape only: JSON object, one to three items, candidate ids that exist in the current snapshot, non-empty title and reason within length caps, integer minutes inside the remaining budget, and non-empty `first_step` / `done_when` when those fields are present. For an existing task or review, the stored title is kept. For a goal, the model’s title, reason, first step, done-when, and minutes are what get saved.

That check does not decide whether the step is true, feasible, safe, or better than the alternatives. The prompt tells the model not to invent experiences, diagnoses, success probabilities, or effect numbers. A prompt line is not a verifier. A fluent and false step can still be stored with a source like `ollama:<model>` and labeled in the interface as “本地模型提案”, including the lead card “建议优先处理”.

Rule cards (`source` `rules`) are templates filled from goals and tasks already on disk. The interface calls them “规则草案”. They can still be accepted. Accepting one does not make the template a measured next action.

Laya ranking selects among existing candidates and does not write an independent explanation. Adaptive and scenario cards come from the local life kernel’s comparison. Their forecast text, when shown, is a model-assumption range. Nothing in this repository shows that range predicts a person’s later outcomes.

Manual decision recommendations are also model text until a person confirms an option. Confirmation writes the person’s choice. It does not score the model.

## Cached recommendations go stale

While the server process stays up, `Planner.tick` skips another Ollama or Laya call when the snapshot digest and the configuration digest match the last attempt and the in-process monotonic clock is still inside the retry window. The window is `auto_recommend_interval_minutes` (default 360, so six hours) after an attempt that did not leave `self.error`. After a provider failure it is 300 seconds. The clock is `time.monotonic()`. It restarts with the process. It is not a durable timestamp and it is not wall-clock proof that the card was reconsidered.

That skip is only the local-model call. When a life model is loaded, `tick` returns before the call. Kernel cards are rebuilt when their snapshot digest changes, not on the six-hour timer. An unchanged digest is still not a measurement of the day.

The first failed model call leaves the rule draft and says so. A later failed refresh leaves the previous cards in place, records the error, and sets the status to `error` instead of calling those cards a rule draft. The previous wording can still be wrong.

Cards for an unchanged digest stay in memory, including earlier model wording. The digest covers stored goals, tasks, recent observations, and a short evidence excerpt. It does not include the calendar, interruptions, energy, or minutes that are actually free. A card can be fresh against the database and stale against the day.

Changing the digest rebuilds draft cards immediately and can replace the previous wording before a new model call finishes. “重新评估” clears the last attempt digest and wakes the scheduler. If a model call is already holding the model lock, that wake does not start a second call; a later pass can. Neither path checks that the new text is true.

The web client sends `proposal_sha256` on accept or dismiss. A mismatch is rejected. That stops an accept of a card whose text already changed. It does not mean the card still on screen is a current or correct judgment.

Stopping the program stops new scheduling. A local model process that already received a request can finish on its own. This application does not run the returned action.

## Budget minutes are not measured free time

`daily_available_minutes` is a setting. The default is 90. The allowed range is 5–480. The homepage number is that setting minus `focus_minutes` (or, if missing, `estimate_minutes`, or else 25) for tasks whose `focus_date` is today. Done tasks are still subtracted that day. Nothing reads a calendar, a clock, or a sensor.

The interface label is “预算中尚未安排的分钟”. The footnote says the figure is the daily budget and that the app does not take calendar time or carry out the action. Those words are labels. They are not a measurement of free time, attention, or energy.

Candidate `minutes` are planning estimates. Accepting a card stores that estimate as `focus_minutes` and reduces the remaining budget. Completing the task does not return the minutes and does not mark the parent goal done.
