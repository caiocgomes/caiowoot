## ADDED Requirements

### Requirement: Drafts consider operator responses already sent in the same turn

When drafts are generated or regenerated for a conversation, the system SHALL detect outbound messages sent after the trigger message (the customer inbound that initiated the draft) and instruct the model to complement, not repeat, what the operator has already said in this turn.

#### Scenario: Regenerate with no prior outbound acts like original flow
- **WHEN** the operator triggers draft regeneration and there are zero outbound messages in this conversation with `created_at >= trigger_message.created_at`
- **THEN** the `user_content` passed to the model SHALL NOT contain a "Respostas já enviadas" section
- **AND** the final instruction SHALL remain "Gere o draft de resposta para a última mensagem do cliente."

#### Scenario: Regenerate with one prior outbound surfaces it explicitly
- **WHEN** the operator triggers draft regeneration and there exists at least one outbound message in this conversation with `created_at >= trigger_message.created_at`
- **THEN** the `user_content` SHALL include a section titled "Respostas já enviadas neste turno" that lists each such outbound with its timestamp and text content in chronological order
- **AND** the final instruction SHALL be rewritten to tell the model that the operator has already begun responding, that the listed messages are the partial response, that the customer has not replied yet, and that the new draft must complement what is still unaddressed without repeating what was already said

#### Scenario: Regenerate with multiple prior outbounds lists them all
- **WHEN** the operator has sent two or more outbound messages after the trigger message with no intervening inbound from the customer
- **THEN** all such outbound messages SHALL appear in the "Respostas já enviadas neste turno" section in chronological order
- **AND** the final instruction text SHALL be identical to the single-outbound case

#### Scenario: Initial draft generation is unchanged
- **WHEN** `generate_drafts` is invoked for a conversation immediately after a new customer inbound and no outbound has been sent since that inbound
- **THEN** the `user_content` and final instruction SHALL match the pre-change behavior exactly (no "Respostas já enviadas" section, original instruction text)

#### Scenario: Proactive followup flow unchanged
- **WHEN** `generate_drafts` or `regenerate_draft` is called with `proactive=True`
- **THEN** the proactive final instruction ("A última mensagem da conversa foi enviada pelo {operator_name}. Gere uma mensagem de continuação natural, retomando o contexto da conversa.") SHALL continue to be used as today
- **AND** the "Respostas já enviadas neste turno" section SHALL NOT be added, because the proactive flow has its own semantics for operator-authored last message

#### Scenario: trigger_message_id parameter is propagated end to end
- **WHEN** `generate_drafts` or `regenerate_draft` is invoked
- **THEN** they SHALL pass the `trigger_message_id` they already receive to `build_prompt_parts`
- **AND** `build_prompt_parts` SHALL use it to query outbound messages from the database, not infer the trigger from the conversation history

#### Scenario: Callers that do not pass trigger_message_id retain legacy behavior
- **WHEN** any caller of `build_prompt_parts` does not pass a `trigger_message_id` (parameter is `None`)
- **THEN** the function SHALL behave exactly as before this change: no outbound detection, no new section, original final instruction
