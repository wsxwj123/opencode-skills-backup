# Zotero 首次设置指南

Note: PyZotero uses **Zotero Web API** (cloud). Desktop app does NOT need to run during API operations — but install it for local sync of created items.

**Step-by-step guide (show this to user if they haven't done it before):**

```
① Register / log in
   → https://www.zotero.org/user/register  (if no account)
   → https://www.zotero.org/user/login

② Get your Library ID (numeric user ID)
   → https://www.zotero.org/settings
   → Scroll to the bottom of the page
   → Look for: "Your user ID for use in API calls is: [NUMBER]"
   → Copy that number — this is your lib_id

③ Create an API key
   → https://www.zotero.org/settings/keys
   → Click "Create new private key"
   → Key Description: e.g. "review-writing-skill"
   → Permissions — check ALL of the following:
       ✅ Allow library access
       ✅ Allow write access           ← required for creating items/collections
       ✅ Allow notes access           ← required for abstract child notes
       ✅ Allow file access            ← required for PDF attachments
   → Click "Save Key"
   → Copy the generated key immediately (shown only once)

④ Test connection
   python3 scripts/zotero_manager.py --status --lib-id [NUMBER] --api-key [KEY]
   Expected output: ✅ Connected to Zotero library ...

⑤ Security rules
   - Write lib_id to outline.md (safe, not secret)
   - NEVER write api_key to any file — ask user at each new session start
   - If 403 Forbidden error: re-ask user for api_key; re-run --status before continuing
```

If `--status` lists multiple libraries (personal + group), show the list and ask user which to use. Write chosen `lib_id` to `outline.md`.
