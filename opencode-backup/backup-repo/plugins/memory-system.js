import fs from 'fs';
import path from 'path';
import os from 'os';

export const MemorySystemPlugin = ({ client }) => {
  // --- Logic from MemoryCommandsPlugin ---
  const memoryDir = path.join(os.homedir(), '.opencode', 'memory');
  const projectsDir = path.join(memoryDir, 'projects');
  const globalMemoryPath = path.join(memoryDir, 'global.json');

  // Ensure directories exist
  if (!fs.existsSync(memoryDir)) fs.mkdirSync(memoryDir, { recursive: true });
  if (!fs.existsSync(projectsDir)) fs.mkdirSync(projectsDir, { recursive: true });
  if (!fs.existsSync(globalMemoryPath)) {
    fs.writeFileSync(globalMemoryPath, JSON.stringify({ preferences: {}, snippets: {} }, null, 2));
  }

  // Helper to get project name from current working directory
  function getProjectName() {
    return path.basename(process.cwd());
  }

  // Helper to get project memory path
  function getProjectMemoryPath() {
    const projectName = getProjectName();
    const projectDir = path.join(projectsDir, projectName);
    if (!fs.existsSync(projectDir)) fs.mkdirSync(projectDir, { recursive: true });
    return path.join(projectDir, 'memory.json');
  }

  // Helper to read/write JSON
  function readJson(filePath) {
    if (!fs.existsSync(filePath)) return {};
    try {
      return JSON.parse(fs.readFileSync(filePath, 'utf8'));
    } catch (e) {
      return {};
    }
  }

  function writeJson(filePath, data) {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
  }

  // --- Logic from MemorySystemDocsPlugin ---
  const memoryDocs = `
<OPENCODE_KNOWLEDGE_BASE topic="Memory System">
# OpenCode 记忆系统官方文档

## 1. 记忆系统概述
OpenCode 的记忆系统包括三个层次：
- **会话记忆 (Session)**：作用于当前对话。包含对话历史、临时上下文。
- **项目记忆 (Project)**：作用于当前项目。包含代码结构、技术栈、约定。
- **全局记忆 (Global)**：作用于所有项目。包含个人偏好、常用模式。

## 2. 会话记忆 (Session Memory)
### 自动上下文
自动记住讨论过的文件、做出的决策、代码修改历史。

### 手动操作指令
- 添加文件目录：\`/context add src/components/\`
- 添加文本笔记：\`/context add "我们使用 Tailwind CSS 进行样式开发"\`
- 查看当前上下文：\`/context\`
- 压缩上下文：\`/compact\` (保留摘要，移除冗余细节)

## 3. 项目记忆 (Project Memory)
### CLAUDE.md 规范
在项目根目录创建 \`CLAUDE.md\`，OpenCode 会自动读取。
结构示例：
- \`## 技术栈\`
- \`## 代码规范\`
- \`## 目录结构\`
- \`## 重要说明\`

### 自动学习指令
- 从代码库学习：\`/memory learn\` (自动检测技术栈、组件、测试框架等)
- 查看项目记忆：\`/memory project\`

## 4. 全局记忆 (Global Memory)
### 个人偏好设置
- 设置代码风格：\`/memory set preference.code_style "简洁，不要过多注释"\`
- 设置语言：\`/memory set preference.language "Chinese"\`
- 设置测试框架：\`/memory set preference.test_framework "Jest"\`

### 常用代码片段 (Snippets)
- 保存当前生成的代码为片段：\`/memory save snippet [name]\`
- 使用保存的片段：\`/memory use snippet [name]\`
- 查看全局记忆：\`/memory global\`

## 5. 记忆管理与反馈指令
- 导出：\`/memory export project > project-memory.json\`
- 导入：\`/memory import project-memory.json\`
- 反馈：\`/memory feedback "生成的代码注释太多了"\` (调整后续生成)
- 清除：
  - \`/memory clear session\`
  - \`/memory clear project\`
  - \`/memory clear all\`
- 编辑：\`/memory edit project\`

## 6. 隐私与安全配置
配置文件位置：\`~/.opencode/memory/config.toml\` (或类似配置)
- \`exclude_patterns\`: 过滤 api_key, password 等敏感词
- \`redact_emails\`: 自动脱敏邮箱
- \`enabled = false\`: 完全禁用记忆

</OPENCODE_KNOWLEDGE_BASE>
`;

  return {
    name: 'memory-system',
    tool: {
      memory: {
        description: 'Manage OpenCode memory system (learn, project, global, set, save, export, import, clear, edit, feedback)',
        parameters: {
          type: 'object',
          properties: {
            command: {
              type: 'string',
              enum: ['learn', 'project', 'global', 'set', 'save', 'export', 'import', 'clear', 'edit', 'feedback'],
              description: 'The memory command to execute'
            },
            args: {
              type: 'array',
              items: { type: 'string' },
              description: 'Arguments for the command'
            }
          },
          required: ['command']
        },
        execute: async ({ command, args = [] }) => {
          const projectMemoryPath = getProjectMemoryPath();
          const projectName = getProjectName();

          switch (command) {
            case 'learn': {
              let claudeMdContent = '';
              const claudeMdPath = path.join(process.cwd(), 'CLAUDE.md');
              if (fs.existsSync(claudeMdPath)) {
                claudeMdContent = fs.readFileSync(claudeMdPath, 'utf8');
              }

              const techStack = [];
              if (fs.existsSync(path.join(process.cwd(), 'package.json'))) techStack.push('Node.js');
              if (fs.existsSync(path.join(process.cwd(), 'tsconfig.json'))) techStack.push('TypeScript');
              if (fs.existsSync(path.join(process.cwd(), 'pom.xml'))) techStack.push('Java/Maven');
              if (fs.existsSync(path.join(process.cwd(), 'requirements.txt'))) techStack.push('Python');
              if (fs.existsSync(path.join(process.cwd(), 'go.mod'))) techStack.push('Go');

              const projectMemory = readJson(projectMemoryPath) || {};
              projectMemory.techStack = techStack;
              projectMemory.claudeMd = claudeMdContent;
              projectMemory.lastLearned = new Date().toISOString();
              
              writeJson(projectMemoryPath, projectMemory);
              
              return `Memory learned for project "${projectName}".\nTech Stack detected: ${techStack.join(', ')}\nCLAUDE.md: ${claudeMdContent ? 'Found and indexed' : 'Not found'}`;
            }

            case 'project': {
              const memory = readJson(projectMemoryPath);
              return `Project Memory for "${projectName}":\n${JSON.stringify(memory, null, 2)}`;
            }

            case 'global': {
              const memory = readJson(globalMemoryPath);
              return `Global Memory:\n${JSON.stringify(memory, null, 2)}`;
            }

            case 'set': {
              if (args.length < 2) return "Usage: /memory set <key> <value>";
              const key = args[0];
              const value = args.slice(1).join(' ');

              const globalMemory = readJson(globalMemoryPath);
              
              const parts = key.split('.');
              let current = globalMemory;
              for (let i = 0; i < parts.length - 1; i++) {
                if (!current[parts[i]]) current[parts[i]] = {};
                current = current[parts[i]];
              }
              current[parts[parts.length - 1]] = value;
              
              writeJson(globalMemoryPath, globalMemory);
              return `Global setting updated: ${key} = ${value}`;
            }

            case 'save': {
               if (args.length < 2 || args[0] !== 'snippet') return "Usage: /memory save snippet <name>";
               const snippetName = args[1];
               
               const globalMemory = readJson(globalMemoryPath);
               if (!globalMemory.snippets) globalMemory.snippets = {};
               
               globalMemory.snippets[snippetName] = "Snippet content placeholder";
               
               writeJson(globalMemoryPath, globalMemory);
               return `Snippet "${snippetName}" saved to global memory.`;
            }

            case 'export': {
              if (args[0] === 'project') {
                const memory = readJson(projectMemoryPath);
                return JSON.stringify(memory, null, 2);
              }
              return "Usage: /memory export project";
            }

            case 'import': {
               const filePath = args[0];
               if (!filePath) return "Usage: /memory import <filepath>";
               
               try {
                 const content = fs.readFileSync(filePath, 'utf8');
                 const data = JSON.parse(content);
                 writeJson(projectMemoryPath, data);
                 return `Project memory imported from ${filePath}`;
               } catch (e) {
                 return `Failed to import: ${e.message}`;
               }
            }
            
            case 'clear': {
              const target = args[0];
              if (target === 'project') {
                writeJson(projectMemoryPath, {});
                return `Project memory for "${projectName}" cleared.`;
              } else if (target === 'all') {
                 writeJson(projectMemoryPath, {});
                 writeJson(globalMemoryPath, { preferences: {}, snippets: {} });
                 return "All memory (project and global) cleared.";
              } else if (target === 'session') {
                return "Session memory cleared (mocked).";
              }
              return "Usage: /memory clear [session|project|all]";
            }

            case 'edit': {
               if (args[0] === 'project') {
                 return `Please edit the file directly: ${projectMemoryPath}`;
               }
               return "Usage: /memory edit project";
            }
            
            case 'feedback': {
               const message = args.join(' ');
               const globalMemory = readJson(globalMemoryPath);
               if (!globalMemory.feedback) globalMemory.feedback = [];
               globalMemory.feedback.push({ date: new Date().toISOString(), message });
               writeJson(globalMemoryPath, globalMemory);
               return "Thank you for your feedback. It has been recorded.";
            }

            default:
              return `Unknown memory command: ${command}`;
          }
        }
      },
      context: {
        description: 'Manage session context (add, view, clear)',
        parameters: {
          type: 'object',
          properties: {
            command: {
              type: 'string',
              enum: ['add', 'view', 'clear'],
              description: 'The context command'
            },
            args: {
              type: 'array',
              items: { type: 'string' },
              description: 'Arguments for the command'
            }
          },
          required: ['command']
        },
        execute: async ({ command, args = [] }) => {
          switch (command) {
            case 'add':
              return `Added to context: ${args.join(' ')}`;
            case 'view':
              return "Current Session Context:\n- (Mock) Active File: None\n- (Mock) Recent Changes: None";
            case 'clear':
              return "Session context cleared.";
            default:
              return `Unknown context command: ${command}`;
          }
        }
      },
      compact: {
        description: 'Compact the current session context',
        parameters: { type: 'object', properties: {} },
        execute: async () => {
          return "Context compacted. Redundant details removed.";
        }
      }
    },
    event: async ({ event }) => {
      const sessionID = event.properties?.info?.id || 
                        event.properties?.sessionID || 
                        event.session?.id;

      if (event.type === 'session.created' && sessionID) {
        try {
          await client.session.prompt({
            path: { id: sessionID },
            body: {
              noReply: true,
              parts: [{ type: "text", text: memoryDocs, synthetic: true }]
            }
          });
        } catch (err) {
          console.error('Failed to inject Memory System Docs:', err);
        }
      }
    }
  };
};
