## 1. Database

- [x] 1.1 Add `last_read_at TIMESTAMP` column to `conversations` in SCHEMA and MIGRATIONS

## 2. Backend

- [x] 2.1 Update `GET /conversations/{id}` to set `last_read_at = CURRENT_TIMESTAMP` on the conversation
- [x] 2.2 Replace `has_unread` with `is_new` and `needs_reply` in `GET /conversations` query
- [x] 2.3 Remove `has_unread` from the ConversationListItem model if it exists

## 3. Frontend

- [x] 3.1 Update `renderConversationList` to use `is_new` and `needs_reply` instead of `has_unread`
- [x] 3.2 Add CSS for green dot indicator and bold name states
- [x] 3.3 Remove old `.unread` border-left style

## 4. Tests

- [x] 4.1 Test: opening conversation updates `last_read_at`
- [x] 4.2 Test: `is_new` true when inbound after null `last_read_at`
- [x] 4.3 Test: `is_new` false after opening conversation
- [x] 4.4 Test: `needs_reply` true when last message is inbound
- [x] 4.5 Test: `needs_reply` false when last message is outbound
