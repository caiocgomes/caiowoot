async function request(url, options = {}) {
  const res = await fetch(url, options);
  if (res.status === 401) {
    window.location.href = '/login.html';
    return res;
  }
  return res;
}

// --- Conversations ---

export async function getConversations() {
  return request("/conversations");
}

export async function getConversation(id) {
  return request(`/conversations/${id}`);
}

export async function sendMessageApi(convId, formData) {
  return request(`/conversations/${convId}/send`, {
    method: "POST",
    body: formData,
  });
}

export async function rewriteTextApi(convId, text) {
  return request(`/conversations/${convId}/rewrite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

export async function regenerateDraftApi(convId, body) {
  return request(`/conversations/${convId}/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function classifyConversationApi(convId) {
  return request(`/conversations/${convId}/classify`, { method: "POST" });
}

export async function updateFunnelApi(convId, body) {
  return request(`/conversations/${convId}/funnel`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function assumeConversationApi(convId) {
  return request(`/conversations/${convId}/assume`, { method: "POST" });
}

// --- Review ---

export async function getReviewItems() {
  return request("/review");
}

export async function validateAnnotationApi(id) {
  return request(`/review/${id}/validate`, { method: "POST" });
}

export async function rejectAnnotationApi(id) {
  return request(`/review/${id}/reject`, { method: "POST" });
}

export async function promoteAnnotationApi(id, ruleText) {
  return request(`/review/${id}/promote`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rule_text: ruleText }),
  });
}

// --- Rules ---

export async function getRules() {
  return request("/rules");
}

export async function toggleRuleApi(id) {
  return request(`/rules/${id}/toggle`, { method: "PATCH" });
}

export async function saveRuleApi(id, ruleText) {
  return request(`/rules/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rule_text: ruleText }),
  });
}

// --- Knowledge ---

export async function getKnowledgeDocs() {
  return request("/knowledge");
}

export async function getKnowledgeDoc(name) {
  return request(`/knowledge/${encodeURIComponent(name)}`);
}

export async function saveKnowledgeDoc(name, content) {
  return request(`/knowledge/${encodeURIComponent(name)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
}

export async function deleteKnowledgeDoc(name) {
  return request(`/knowledge/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
}

export async function createKnowledgeDoc(name, content) {
  return request("/knowledge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, content }),
  });
}

// --- Settings ---

export async function getSettingsProfile() {
  return request("/api/settings/profile");
}

export async function saveSettingsProfile(displayName, context) {
  return request("/api/settings/profile", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: displayName, context: context }),
  });
}

export async function getSettingsPrompts() {
  return request("/api/settings/prompts");
}

export async function saveSettingsPrompts(updates) {
  return request("/api/settings/prompts", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
}

export async function getIsAdmin() {
  return request("/api/settings/is-admin");
}

export async function resetPromptApi(key) {
  return request("/api/settings/prompts", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ [key]: null }),
  });
}

// --- Attachments ---

export async function getAttachments() {
  return request("/api/attachments");
}

export async function getAttachmentBlob(filename) {
  return request(`/api/attachments/${encodeURIComponent(filename)}`);
}

// --- Scheduled Sends ---

export async function getScheduledSends(convId) {
  return request(`/conversations/${convId}/scheduled`);
}

export async function createScheduledSend(convId, body) {
  return request(`/conversations/${convId}/schedule`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function deleteScheduledSend(sendId) {
  return request(`/scheduled-sends/${sendId}`, { method: "DELETE" });
}

// --- Campaigns ---

export async function getCampaigns() {
  return request("/campaigns");
}

export async function getCampaign(id) {
  return request(`/campaigns/${id}`);
}

export async function createCampaignApi(formData) {
  return request("/campaigns", { method: "POST", body: formData });
}

export async function generateVariationsApi(campaignId) {
  return request(`/campaigns/${campaignId}/generate-variations`, { method: "POST" });
}

export async function editVariationApi(campaignId, variationIdx, text) {
  return request(`/campaigns/${campaignId}/variations/${variationIdx}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ variation_text: text }),
  });
}

export async function toggleVariationApi(campaignId, variationId) {
  return request(`/campaigns/${campaignId}/variations/${variationId}/toggle`, { method: "PATCH" });
}

export async function startCampaignApi(id) {
  return request(`/campaigns/${id}/start`, { method: "POST" });
}

export async function pauseCampaignApi(id) {
  return request(`/campaigns/${id}/pause`, { method: "POST" });
}

export async function resumeCampaignApi(id) {
  return request(`/campaigns/${id}/resume`, { method: "POST" });
}

export async function retryCampaignApi(id) {
  return request(`/campaigns/${id}/retry`, { method: "POST" });
}
