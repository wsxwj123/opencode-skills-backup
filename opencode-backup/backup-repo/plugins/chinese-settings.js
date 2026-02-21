/**
 * Chinese Settings Plugin for OpenCode.ai
 * 
 * Automatically injects Chinese language preference and Git proxy settings
 * into every new session.
 */

export const ChineseSettingsPlugin = async ({ client }) => {
  const customInstructions = `<EXTREMELY_IMPORTANT>
请始终使用简体中文回复用户的所有问题和请求。禁止使用英文回复,除非用户要求!

在执行以下操作时，确保使用 HTTP 代理 http://127.0.0.1:7897：
- git clone 命令
- 任何连接 GitHub 的操作
- 下载或克隆远程仓库

Git 全局配置已设置代理，所有 Git 操作会自动使用该代理。
</EXTREMELY_IMPORTANT>`;

  // Helper to inject instructions
  const injectInstructions = async (sessionID, compact = false) => {
    const content = compact 
      ? `<EXTREMELY_IMPORTANT>
请始终使用简体中文回复用户的所有问题和请求。禁止使用英文回复,除非用户要求!
Git 操作使用代理 http://127.0.0.1:7897。
</EXTREMELY_IMPORTANT>`
      : customInstructions;

    try {
      await client.session.prompt({
        path: { id: sessionID },
        body: {
          noReply: true,
          parts: [{ type: "text", text: content, synthetic: true }]
        }
      });
      return true;
    } catch (err) {
      console.error('Failed to inject Chinese settings:', err);
      return false;
    }
  };

  return {
    event: async ({ event }) => {
      // Extract sessionID from various event structures
      const getSessionID = () => {
        return event.properties?.info?.id ||
               event.properties?.sessionID ||
               event.session?.id;
      };

      // Inject at session creation (full instructions)
      if (event.type === 'session.created') {
        const sessionID = getSessionID();
        if (sessionID) {
          await injectInstructions(sessionID, false);
        }
      }

      // Re-inject after compaction (compact version to save tokens)
      if (event.type === 'session.compacted') {
        const sessionID = getSessionID();
        if (sessionID) {
          await injectInstructions(sessionID, true);
        }
      }
    }
  };
};
